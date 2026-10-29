import io
import json
import logging
from uuid import uuid4

import pytest
from app.platform.errors import DomainError, NotFoundError
from app.platform.logging import JsonFormatter, log, logger, request_id
from app.platform.storage import PrivateStorage


def test_log_redacts_context_exception_and_preserves_correlation():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    correlation = str(uuid4())
    document_id = str(uuid4())
    token = request_id.set(correlation)
    try:
        try:
            raise RuntimeError("secret key=sk-private IBAN=SK123 provider raw content")
        except RuntimeError:
            log(
                "document.failed",
                level=logging.ERROR,
                documentId=document_id,
                apiKey="sk-private",
                filename="private-name.pdf",
                amount="1234.00",
                cookie="private-session",
                errorCode="PROVIDER_FAILED",
                exc_info=True,
            )
    finally:
        logger.removeHandler(handler)
        request_id.reset(token)
    result = json.loads(stream.getvalue())
    assert result["requestId"] == correlation
    assert result["documentId"] == document_id
    assert result["event"] == "document.failed"
    assert result["level"] == "ERROR"
    assert result["errorCode"] == "PROVIDER_FAILED"
    assert result["stack"]
    for secret in [
        "sk-private",
        "SK123",
        "private-name",
        "1234.00",
        "private-session",
        "provider raw",
    ]:
        assert secret not in stream.getvalue()


def test_private_storage_is_immutable_and_rejects_traversal(tmp_path):
    storage = PrivateStorage(tmp_path / "files")
    document_id = uuid4()
    storage.put(document_id, b"document content")
    assert storage.read(document_id) == b"document content"
    assert (storage.root / str(document_id)).stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        storage.put(document_id, b"replacement")
    assert storage.read(document_id) == b"document content"
    with pytest.raises(ValueError):
        storage.read("../../etc/passwd")
    with pytest.raises(NotFoundError):
        storage.read(uuid4())
    with pytest.raises(DomainError) as error:
        storage.put(uuid4(), b"x" * (20 * 1024 * 1024 + 1))
    assert error.value.status == 413
