import asyncio
import os
import time
from uuid import uuid4

import pytest
from app.documents.cleanup import cleanup_orphans
from app.documents.service import create_documents
from app.main import create_app
from app.platform.errors import DomainError
from app.platform.jobs import run_once
from app.platform.settings import get_settings
from app.platform.storage import PrivateStorage
from app.platform.upload_limit import UploadBodyLimit
from app.worker import build_registry
from fastapi.testclient import TestClient
from sqlalchemy import func, select


@pytest.mark.parametrize("declared", [True, False])
def test_body_limit_rejects_before_parsing(monkeypatch, declared):
    monkeypatch.setenv("DOCUMENT_MAX_BATCH_BYTES", "1")
    called = []

    async def downstream(*args):
        called.append(True)

    messages = iter(
        [{"type": "http.request", "body": b"x" * (1024 * 1024 + 2), "more_body": False}]
    )
    sent = []

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    asyncio.run(
        UploadBodyLimit(downstream)(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/v1/documents",
                "headers": [(b"content-length", b"1048578")] if declared else [],
            },
            receive,
            send,
        )
    )
    assert not called
    assert sent[0]["status"] == 413
    assert b'"code":"UPLOAD_TOO_LARGE"' in sent[1]["body"]


def test_storage_refuses_unsupported_runtime(monkeypatch, tmp_path):
    monkeypatch.delattr(os, "O_NOFOLLOW")
    with pytest.raises(DomainError) as failure:
        PrivateStorage(tmp_path)
    assert failure.value.code == "STORAGE_UNAVAILABLE"


def test_private_storage_never_follows_links(tmp_path):
    storage = PrivateStorage(tmp_path / "files")
    external = tmp_path / "external"
    external.write_bytes(b"private")
    document_id = uuid4()
    (storage.root / str(document_id)).symlink_to(external)
    with pytest.raises(OSError):
        storage.read(document_id)
    with pytest.raises(FileExistsError):
        storage.put(document_id, b"replacement")
    assert external.read_bytes() == b"private"


def test_production_upload_worker_preview_and_immutable_sources(database, monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_PATH", str(tmp_path))
    get_settings.cache_clear()
    registry = build_registry()
    from app.documents.service import process_document

    assert registry.handlers["document.process"] is process_document
    with TestClient(
        create_app(), base_url="http://localhost", headers={"Origin": "http://localhost:5173"}
    ) as client:
        response = client.post(
            "/api/v1/documents", files={"files": ("input.csv", b"key,value\nName,42\n", "text/csv")}
        )
        assert response.status_code == 201, response.text
        document_id = response.json()["data"][0]["id"]
        assert client.get(f"/api/v1/documents/{document_id}/normalized").status_code == 409
        assert run_once(database, registry)
        normalized = client.get(f"/api/v1/documents/{document_id}/normalized").json()
        assert [u["text"] for u in normalized["data"]["units"]] == ["key", "value", "Name", "42"]
        assert (
            client.get(f"/api/v1/documents/{document_id}/content").content
            == b"key,value\nName,42\n"
        )
        assert client.post(f"/api/v1/documents/{document_id}/retries").status_code == 409
        assert not run_once(database, registry)
        assert client.get(f"/api/v1/documents/{document_id}/normalized").json() == normalized


def test_cleanup_preserves_accepted_and_active_uploads(database, monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_PATH", str(tmp_path))
    get_settings.cache_clear()
    with database() as session:
        accepted = create_documents(session, [("input.csv", "text/csv", b"name,value\nx,1")])[0]
    orphan, active = uuid4(), uuid4()
    storage = PrivateStorage(tmp_path)
    storage.put(orphan, b"orphan")
    storage.put(active, b"in progress")
    for path in tmp_path.iterdir():
        os.utime(path, (time.time() - 7200,) * 2)
    with database.begin() as session:
        session.execute(select(func.pg_advisory_xact_lock(-1 - (active.int % (2**63 - 1)))))
        assert cleanup_orphans(database) == 1
        assert storage.read(active) == b"in progress"
        assert storage.read(accepted.id)
    assert cleanup_orphans(database) == 1
    assert storage.read(accepted.id)


def test_recovery_uses_original_correlation_once(database, monkeypatch, tmp_path):
    import io
    import json
    import logging

    from app.documents.service import reconcile_interrupted
    from app.platform.logging import JsonFormatter, logger, request_id
    from app.platform.models import Job

    monkeypatch.setenv("FILE_STORAGE_PATH", str(tmp_path))
    get_settings.cache_clear()
    correlation = str(uuid4())
    token = request_id.set(correlation)
    try:
        with database() as session:
            document = create_documents(session, [("safe.csv", "text/csv", b"name,value\nx,1")])[0]
    finally:
        request_id.reset(token)
    with database.begin() as session:
        job = session.scalar(select(Job))
        job.status, job.attempt = "failed", 3
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    try:
        for _ in range(2):
            with database() as session:
                reconcile_interrupted(session)
    finally:
        logger.removeHandler(handler)
    events = [json.loads(line) for line in output.getvalue().splitlines()]
    assert len(events) == 1
    assert events[0]["requestId"] == correlation
    assert events[0]["documentId"] == str(document.id)
    assert events[0]["attempt"] == 3
    assert events[0]["durationMs"] >= 0
