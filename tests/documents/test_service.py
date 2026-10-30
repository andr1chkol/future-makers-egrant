import io
import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from alembic import command
from app.documents import service
from app.documents.models import StoredDocument, StoredSourceUnit
from app.documents.normalization import normalize
from app.documents.settings import DocumentSettings
from app.platform.contracts import Document, NormalizedDocument
from app.platform.errors import ConflictError, DomainError, NotFoundError
from app.platform.jobs import JobRegistry, claim, run_once
from app.platform.logging import JsonFormatter, logger, request_id
from app.platform.models import Job
from app.platform.settings import get_settings
from sqlalchemy import func, select, text

from .conftest import migration_config


def upload(factory, content, filename="source.csv", media_type="text/csv"):
    with factory() as session:
        return service.create_documents(session, [(filename, media_type, content)])[0]


def registry():
    result = JobRegistry()
    result.register_handler("document.process", service.process_document)
    return result


def read(factory, document_id):
    with factory() as session:
        return service.get_document(session, document_id)


def make_jobs_available(factory):
    with factory.begin() as session:
        for job in session.scalars(select(Job).where(Job.status == "queued")):
            job.available_at = session.scalar(select(func.now())) - timedelta(seconds=1)


def test_real_csv_upload_process_read_and_immutable_sources(
    document_database, storage_compatibility, csv_content
):
    document = upload(document_database, csv_content, "../../private/Žiadosť.csv")
    assert document.filename == "Žiadosť.csv" and document.status == "uploaded"
    with document_database() as session:
        with pytest.raises(ConflictError):
            service.get_normalized(session, document.id)
    assert run_once(document_database, registry())
    with document_database() as session:
        document, original = service.get_content(session, document.id)
        sources = service.get_normalized(session, document.id)
        assert original == csv_content
        assert document.status == "ready"
        assert sources.document_id == document.id and len(sources.units) == 6
        assert session.scalar(select(func.count()).select_from(StoredSourceUnit)) == 6
    with document_database() as session:
        service.process_document(session, document.id)
    with document_database() as session:
        assert service.get_normalized(session, document.id) == sources
        assert session.get(StoredDocument, document.id).attempts == 1
    with document_database() as session, pytest.raises(ConflictError):
        service.retry_document(session, document.id)
    root = get_settings().file_storage_path
    assert [path.name for path in root.iterdir()] == [str(document.id)]


def test_duplicate_uploads_are_separate_under_concurrency(document_database, csv_content):
    with ThreadPoolExecutor(max_workers=2) as pool:
        documents = list(pool.map(lambda _: upload(document_database, csv_content), range(2)))
    assert documents[0].id != documents[1].id
    assert len([document for document in documents if document.duplicate_of]) == 1
    duplicate = next(document for document in documents if document.duplicate_of)
    assert duplicate.duplicate_of in {document.id for document in documents}
    assert duplicate.warnings[0].code == "DUPLICATE_DOCUMENT"
    assert len(list(get_settings().file_storage_path.iterdir())) == 2


def test_preflight_rejects_whole_invalid_batch_without_jobs(document_database, csv_content):
    with document_database() as session, pytest.raises(DomainError):
        service.create_documents(
            session,
            [("good.csv", "text/csv", csv_content), ("bad.pdf", "application/pdf", b"%PDF-broken")],
        )
    with document_database() as session:
        assert session.scalar(select(func.count()).select_from(StoredDocument)) == 0
        assert session.scalar(select(func.count()).select_from(Job)) == 0


def test_mixed_processing_results_and_manual_retry(
    document_database, storage_compatibility, csv_content, png_content, monkeypatch
):
    good = upload(document_database, csv_content)
    image = upload(document_database, png_content, "scan.png", "image/png")
    while run_once(document_database, registry()):
        pass
    assert read(document_database, good.id).status == "ready"
    assert read(document_database, image.id).error.code == "OCR_UNAVAILABLE"
    with document_database() as session:
        service.retry_document(session, image.id)
    with document_database() as session, pytest.raises(ConflictError):
        service.retry_document(session, image.id)
    original_parser = service.parse_document

    def fake_provider(content, media_type, document_id, **kwargs):
        if kwargs.get("validation_only"):
            return original_parser(content, media_type, document_id, **kwargs)
        return normalize(
            content, media_type, document_id, DocumentSettings(), ocr=lambda *_: "Readable scan"
        )

    monkeypatch.setattr(service, "parse_document", fake_provider)
    assert run_once(document_database, registry())
    assert read(document_database, image.id).status == "ready"


def test_timeout_has_bounded_automatic_retries(
    document_database, storage_compatibility, csv_content, monkeypatch
):
    document = upload(document_database, csv_content)

    def timeout(*args, **kwargs):
        raise DomainError("OCR_TIMEOUT", 502, "OCR exceeded its time limit")

    monkeypatch.setattr(service, "parse_document", timeout)
    for attempt in range(1, 4):
        make_jobs_available(document_database)
        assert run_once(document_database, registry())
        with document_database() as session:
            assert session.get(StoredDocument, document.id).attempts == attempt
            assert service.get_document(session, document.id).status == (
                "uploaded" if attempt < 3 else "failed"
            )
            assert session.scalar(select(func.count()).select_from(StoredSourceUnit)) == 0
    assert not run_once(document_database, registry())
    assert read(document_database, document.id).error.code == "OCR_TIMEOUT"
    with document_database() as session, pytest.raises(ConflictError):
        service.retry_document(session, document.id)


def test_restart_reclaims_lease_without_duplicate_sources(
    document_database, storage_compatibility, csv_content
):
    document = upload(document_database, csv_content)
    with document_database.begin() as session:
        job = claim(session)
        job.lease_until = session.scalar(select(func.now())) - timedelta(seconds=1)
        record = session.get(StoredDocument, document.id)
        record.status, record.attempts, record.processing_token = "processing", 1, job.lease_token
    assert run_once(document_database, registry())
    with document_database() as session:
        assert service.get_document(session, document.id).status == "ready"
        assert session.get(StoredDocument, document.id).attempts == 2
        assert session.scalar(select(func.count()).select_from(StoredSourceUnit)) == 6


def test_terminal_worker_crash_is_persisted_as_failure(document_database, csv_content):
    document = upload(document_database, csv_content)
    with document_database.begin() as session:
        job = claim(session)
        job.attempt = job.max_attempts
        job.lease_until = session.scalar(select(func.now())) - timedelta(seconds=1)
        record = session.get(StoredDocument, document.id)
        record.status, record.attempts = "processing", 3
    with document_database() as session:
        assert service.get_document(session, document.id).error.code == "PROCESSING_INTERRUPTED"
    with document_database() as session:
        service.reconcile_interrupted(session)
    with document_database() as session:
        assert session.get(StoredDocument, document.id).status == "failed"
        with pytest.raises(ConflictError):
            service.get_normalized(session, document.id)
    assert not run_once(document_database, registry())


def test_late_worker_cannot_publish_after_reclaimed_job(
    document_database, storage_compatibility, csv_content, monkeypatch
):
    document = upload(document_database, csv_content)
    entered, resume = threading.Event(), threading.Event()
    original_parser = service.parse_document
    calls = 0

    def delayed_parser(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            entered.set()
            assert resume.wait(15)
        return original_parser(*args, **kwargs)

    monkeypatch.setattr(service, "parse_document", delayed_parser)
    with ThreadPoolExecutor(max_workers=1) as pool:
        stale_worker = pool.submit(run_once, document_database, registry())
        assert entered.wait(15)
        with document_database.begin() as session:
            job = session.scalar(select(Job))
            job.lease_until = session.scalar(select(func.now())) - timedelta(seconds=1)
        assert run_once(document_database, registry())
        resume.set()
        assert stale_worker.result(timeout=15)
    with document_database() as session:
        assert service.get_document(session, document.id).status == "ready"
        assert session.scalar(select(func.count()).select_from(StoredSourceUnit)) == 6


def test_no_database_transaction_while_parsing(
    document_database, storage_compatibility, csv_content, monkeypatch
):
    document = upload(document_database, csv_content)
    with document_database.begin() as session:
        claim(session)
    original_parser = service.parse_document
    with document_database() as session:

        def observe(*args, **kwargs):
            assert not session.in_transaction()
            return original_parser(*args, **kwargs)

        monkeypatch.setattr(service, "parse_document", observe)
        service.process_document(session, document.id)


def test_migration_upgrade_downgrade(document_database):
    with document_database() as session:
        assert (
            session.scalar(text("SELECT version_num FROM alembic_version"))
            == "0503_documents_assembly"
        )
    command.downgrade(migration_config(), "0001_platform")
    with document_database() as session:
        assert session.scalar(text("SELECT to_regclass('public.documents')")) is None
    command.upgrade(migration_config(), "documents@head")


def test_http_contract_access_and_normalized_not_ready(
    client, document_database, storage_compatibility, csv_content, monkeypatch
):
    response = client.post(
        "/api/v1/documents", files=[("files", ("sample.csv", csv_content, "text/csv"))]
    )
    assert response.status_code == 201, response.text
    document = Document.model_validate(response.json()["data"][0])
    assert client.get(f"/api/v1/documents/{document.id}/normalized").status_code == 409
    assert client.get("/api/v1/documents").json()["pagination"]["total"] == 1
    assert client.get("/api/v1/documents?limit=201").status_code == 422
    assert client.get(f"/api/v1/documents/{uuid4()}").status_code == 404
    assert run_once(document_database, registry())
    response = client.get(f"/api/v1/documents/{document.id}/normalized")
    assert response.status_code == 200
    NormalizedDocument.model_validate(response.json()["data"])
    content = client.get(f"/api/v1/documents/{document.id}/content")
    assert content.content == csv_content
    assert content.headers["cache-control"] == "no-store"
    assert content.headers["x-content-type-options"] == "nosniff"
    monkeypatch.setenv("DEV_AUTH_BYPASS", "false")
    monkeypatch.setenv("ACCESS_CODE", "test-only-access-code-long-enough")
    get_settings.cache_clear()
    for path in [
        f"/api/v1/documents/{document.id}/content",
        f"/api/v1/documents/{document.id}/normalized",
        "/api/v1/documents",
    ]:
        assert client.get(path).status_code == 401


def test_upload_failure_is_safe_and_oversize_rejected(client, monkeypatch):
    monkeypatch.setenv("DOCUMENT_MAX_BYTES", "10")
    response = client.post(
        "/api/v1/documents", files=[("files", ("secret-name.csv", b"x" * 11, "text/csv"))]
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "UPLOAD_TOO_LARGE"
    assert "secret-name" not in response.text


def test_structured_events_correlation_and_redaction(
    document_database, storage_compatibility, monkeypatch
):
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    correlation = str(uuid4())
    token = request_id.set(correlation)
    secret = "sk-" + "private-provider-key-Jana-Novak-iban-SK3112000000198742637541"
    try:
        document = upload(
            document_database, f"name,value\nJana Novak,{secret}".encode(), f"{secret}.csv"
        )
        upload(document_database, f"name,value\nJana Novak,{secret}".encode())
        assert run_once(document_database, registry())
        logs = [json.loads(line) for line in output.getvalue().splitlines()]
        events = {entry["event"] for entry in logs}
        assert {
            "document.uploaded",
            "document.duplicate_detected",
            "document.processing_started",
            "document.ready",
        } <= events
        for entry in logs:
            assert entry["requestId"] == correlation
        assert next(entry for entry in logs if entry["event"] == "document.ready")["attempt"] == 1
        assert secret not in output.getvalue() and "Jana Novak" not in output.getvalue()
        assert str(document.id) in output.getvalue()
    finally:
        request_id.reset(token)
        logger.removeHandler(handler)


def test_missing_document_is_not_an_empty_success(document_database):
    with document_database() as session, pytest.raises(NotFoundError):
        service.get_normalized(session, uuid4())


def test_windows_storage_limitation_returns_explicit_failure(document_database, csv_content):
    if hasattr(os, "O_NOFOLLOW"):
        pytest.skip("POSIX storage supports the required protection flag")
    document = upload(document_database, csv_content)
    with document_database() as session, pytest.raises(DomainError, match="STORAGE_UNAVAILABLE"):
        service.get_content(session, document.id)


def test_transient_failure_stays_pollable_until_automatic_success(
    document_database, storage_compatibility, csv_content, monkeypatch
):
    document = upload(document_database, csv_content)
    original_parser = service.parse_document
    calls = 0

    def flaky(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise DomainError("OCR_TIMEOUT", 502, "OCR exceeded its time limit")
        return original_parser(*args, **kwargs)

    monkeypatch.setattr(service, "parse_document", flaky)
    assert run_once(document_database, registry())
    waiting = read(document_database, document.id)
    assert waiting.status == "uploaded" and waiting.error.code == "OCR_TIMEOUT"
    make_jobs_available(document_database)
    assert run_once(document_database, registry())
    assert read(document_database, document.id).status == "ready"


def test_concurrent_manual_retries_enqueue_once(
    document_database, storage_compatibility, png_content
):
    document = upload(document_database, png_content, "photo.png", "image/png")
    assert run_once(document_database, registry())

    def retry():
        with document_database() as session:
            try:
                service.retry_document(session, document.id)
                return "accepted"
            except ConflictError:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: retry(), range(2))) == ["accepted", "conflict"]
    with document_database() as session:
        assert session.scalar(select(func.count()).select_from(Job)) == 2


def test_storage_failure_and_log_redaction(
    document_database, storage_compatibility, csv_content, monkeypatch
):
    document = upload(document_database, csv_content)
    secret = "sk-" + "live-private-token-Jana-Novak-SK3112000000198742637541"
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    def fail(*args):
        raise OSError(secret)

    monkeypatch.setattr("app.platform.storage.PrivateStorage.read", fail)
    try:
        assert run_once(document_database, registry())
        assert read(document_database, document.id).error.code == "STORAGE_UNAVAILABLE"
        failure = next(
            json.loads(line)
            for line in output.getvalue().splitlines()
            if json.loads(line)["event"] == "document.failed"
        )
        assert failure["level"] == "ERROR" and failure["errorCode"] == "STORAGE_UNAVAILABLE"
        assert failure["attempt"] == 1 and "durationMs" in failure
        assert secret not in output.getvalue()
    finally:
        logger.removeHandler(handler)


def test_stored_content_hash_mismatch_never_publishes_sources(
    document_database, storage_compatibility, csv_content, monkeypatch
):
    document = upload(document_database, csv_content)
    monkeypatch.setattr("app.platform.storage.PrivateStorage.read", lambda *_: b"changed,file")
    assert run_once(document_database, registry())
    assert read(document_database, document.id).error.code == "CONTENT_HASH_MISMATCH"
    with document_database() as session:
        assert session.scalar(select(func.count()).select_from(StoredSourceUnit)) == 0
