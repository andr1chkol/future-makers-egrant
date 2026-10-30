import logging
import sys
import time
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.documents.models import StoredDocument, StoredSourceUnit
from app.documents.normalization import declared_media_type
from app.documents.parsing import parse_document
from app.documents.settings import DocumentSettings
from app.platform.contracts import Document, NormalizedDocument, SourceUnit
from app.platform.errors import ConflictError, DomainError, NotFoundError
from app.platform.jobs import JobPayload, enqueue
from app.platform.logging import log
from app.platform.models import Job
from app.platform.settings import get_settings
from app.platform.storage import PrivateStorage


def storage() -> PrivateStorage:
    return PrivateStorage(get_settings().file_storage_path)


def _record(session: Session, document_id: UUID, *, lock=False) -> StoredDocument:
    query = select(StoredDocument).where(StoredDocument.id == document_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    record = session.scalar(query)
    if record is None:
        raise NotFoundError()
    return record


def _dto(session: Session, record: StoredDocument) -> Document:
    status, error = record.status, record.error
    if status in {"uploaded", "processing"} and record.job_id:
        job = session.get(Job, record.job_id)
        # A worker killed on its last lease cannot update the document. Reads expose that failure.
        if job and (
            job.status == "failed"
            or (
                job.status == "running"
                and job.attempt >= job.max_attempts
                and job.lease_until is not None
                and job.lease_until <= datetime.now(UTC)
            )
        ):
            status = "failed"
            error = {
                "code": "PROCESSING_INTERRUPTED",
                "message": "Document worker was interrupted",
                "details": None,
            }
    return Document(
        id=record.id,
        filename=record.filename,
        media_type=record.media_type,
        status=status,
        content_hash=record.content_hash,
        duplicate_of=record.duplicate_of,
        created_at=record.created_at,
        page_count=record.page_count,
        warnings=record.warnings,
        error=error,
    )


def get_document(session: Session, document_id: UUID) -> Document:
    return _dto(session, _record(session, document_id))


def reconcile_interrupted(session: Session) -> None:
    """Persist terminal worker crashes; invoke periodically and before HTTP status reads."""
    failed = []
    with session.begin():
        records = session.scalars(
            select(StoredDocument)
            .join(Job, StoredDocument.job_id == Job.id)
            .where(
                StoredDocument.status.in_(["uploaded", "processing"]),
                or_(
                    Job.status == "failed",
                    and_(
                        Job.status == "running",
                        Job.attempt >= Job.max_attempts,
                        Job.lease_until < func.now(),
                    ),
                ),
            )
            .with_for_update(of=StoredDocument, skip_locked=True)
        )
        for record in records:
            record.status = "failed"
            record.error = {
                "code": "PROCESSING_INTERRUPTED",
                "message": "Document worker was interrupted",
                "details": None,
            }
            failed.append((record.id, record.job_id, record.attempts))
    for document_id, job_id, attempt in failed:
        log(
            "document.failed",
            level=logging.ERROR,
            documentId=document_id,
            jobId=job_id,
            attempt=attempt,
            errorCode="PROCESSING_INTERRUPTED",
        )


def list_documents(session: Session, limit: int, offset: int) -> tuple[list[Document], int]:
    total = session.scalar(select(func.count()).select_from(StoredDocument))
    records = session.scalars(
        select(StoredDocument)
        .order_by(
            StoredDocument.created_at.desc(),
            StoredDocument.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return [_dto(session, record) for record in records], total


def create_documents(
    session: Session, uploads: list[tuple[str, str | None, bytes]]
) -> list[Document]:
    """Preflight the entire request before accepting files; later processing fails independently."""
    started = time.monotonic()
    settings = DocumentSettings()
    if not uploads or len(uploads) > settings.max_batch_files:
        raise DomainError("BATCH_LIMIT", 413, "Invalid number of files in upload batch")
    if sum(len(content) for _, _, content in uploads) > settings.max_batch_bytes:
        raise DomainError("BATCH_LIMIT", 413, "Upload batch exceeds the configured size limit")
    prepared = []
    for filename, declared, content in uploads:
        document_id = uuid4()
        media_type = declared_media_type(filename, declared, content)
        metadata = parse_document(content, media_type, document_id, validation_only=True)
        # Filenames are display metadata only; storage accepts generated UUIDs exclusively.
        display_name = filename.replace("\\", "/").rsplit("/", 1)[-1]
        display_name = "".join(character for character in display_name if ord(character) >= 32)[
            :255
        ]
        prepared.append((document_id, display_name or "document", media_type, metadata, content))
    records = []
    with session.begin():
        # Acquire all hash locks in one order, including requests with reversed file order.
        for hash_lock in sorted({int(sha256(entry[4]).hexdigest()[:15], 16) for entry in prepared}):
            session.execute(select(func.pg_advisory_xact_lock(hash_lock)))
        for document_id, filename, media_type, metadata, content in prepared:
            content_hash = sha256(content).hexdigest()
            duplicate = session.scalar(
                select(StoredDocument)
                .where(
                    StoredDocument.content_hash == content_hash,
                )
                .order_by(StoredDocument.created_at, StoredDocument.id)
                .limit(1)
            )
            record = StoredDocument(
                id=document_id,
                filename=filename,
                media_type=media_type,
                content_hash=content_hash,
                duplicate_of=duplicate.id if duplicate else None,
                page_count=metadata.page_count,
                warnings=[
                    {
                        "code": "DUPLICATE_DOCUMENT",
                        "message": "An identical file was already uploaded",
                        "fieldKey": None,
                        "tableKey": None,
                        "rowId": None,
                    }
                ]
                if duplicate
                else [],
                error=None,
            )
            try:
                storage().put(document_id, content)
            except OSError:
                raise DomainError(
                    "STORAGE_UNAVAILABLE", 503, "Private file storage is unavailable"
                ) from None
            session.add(record)
            session.flush()
            record.job_id = enqueue(
                session, "document.process", JobPayload(resource_id=document_id)
            )
            records.append(record)
    for record in records:
        log(
            "document.uploaded",
            documentId=record.id,
            attempt=0,
            durationMs=round((time.monotonic() - started) * 1000),
        )
        if record.duplicate_of:
            log(
                "document.duplicate_detected",
                level=logging.WARNING,
                documentId=record.id,
                attempt=0,
            )
    return [_dto(session, record) for record in records]


def get_content(session: Session, document_id: UUID) -> tuple[Document, bytes]:
    document = get_document(session, document_id)
    try:
        return document, storage().read(document_id)
    except (OSError, AttributeError):
        raise DomainError(
            "STORAGE_UNAVAILABLE", 503, "Private file storage is unavailable"
        ) from None


def get_normalized(session: Session, document_id: UUID) -> NormalizedDocument:
    """Return immutable ready sources; reads never commit or pretend pending sources are empty."""
    document = get_document(session, document_id)
    if document.status != "ready":
        raise ConflictError()
    units = session.scalars(
        select(StoredSourceUnit)
        .where(
            StoredSourceUnit.document_id == document_id,
        )
        .order_by(StoredSourceUnit.ordinal)
    )
    return NormalizedDocument(
        document_id=document_id,
        units=[
            SourceUnit(
                id=unit.id,
                text=unit.text,
                page=unit.page,
                sheet=unit.sheet,
                cell=unit.cell,
            )
            for unit in units
        ],
    )


def retry_document(session: Session, document_id: UUID) -> Document:
    with session.begin():
        record = _record(session, document_id, lock=True)
        document = _dto(session, record)
        job = session.get(Job, record.job_id) if record.job_id else None
        if document.status != "failed" or record.attempts >= 3:
            raise ConflictError()
        if job and job.status in {"queued", "running"}:
            raise ConflictError()
        record.status, record.error, record.processing_token = "uploaded", None, None
        record.job_id = enqueue(session, "document.process", JobPayload(resource_id=document_id))
        # Keep a lifetime cap, including manual retries, rather than resetting a poison document.
        next_job = session.get(Job, record.job_id)
        next_job.max_attempts = 3 - record.attempts
    log(
        "job.retry_scheduled",
        level=logging.WARNING,
        documentId=document_id,
        jobId=record.job_id,
        attempt=record.attempts,
    )
    return _dto(session, record)


def process_document(session: Session, document_id: UUID) -> None:
    """Worker handler; claim/finalization transactions fence late workers by the platform lease."""
    started = time.monotonic()
    with session.begin():
        record = _record(session, document_id, lock=True)
        if record.status == "ready":
            return
        job = session.get(Job, record.job_id)
        now = session.scalar(select(func.now()))
        if not job or job.status != "running" or not job.lease_until or job.lease_until <= now:
            raise ConflictError()
        token, job_id = job.lease_token, job.id
        if record.processing_token == token:
            return
        if record.attempts >= 3:
            return
        record.processing_token = token
        record.attempts += 1
        record.status, record.error = "processing", None
        attempt, media_type, content_hash = record.attempts, record.media_type, record.content_hash
    log("document.processing_started", documentId=document_id, jobId=job_id, attempt=attempt)
    result, failure, failure_trace = None, None, None
    try:
        # No database transaction remains open during file parsing or OCR.
        try:
            content = storage().read(document_id)
        except (OSError, AttributeError):
            raise DomainError(
                "STORAGE_UNAVAILABLE", 503, "Private file storage is unavailable"
            ) from None
        if sha256(content).hexdigest() != content_hash:
            raise DomainError(
                "CONTENT_HASH_MISMATCH", 422, "Stored document integrity check failed"
            )
        result = parse_document(content, media_type, document_id)
    except DomainError as error:
        failure = error
    except Exception:
        failure = DomainError("PROCESSING_FAILED", 502, "Document processing failed")
        failure_trace = sys.exc_info()
    with session.begin():
        record = _record(session, document_id, lock=True)
        job = session.scalar(
            select(Job)
            .where(Job.id == job_id)
            .with_for_update()
            .execution_options(
                populate_existing=True,
            )
        )
        now = session.scalar(select(func.now()))
        # Ready sources never change. A reclaimed or expired lease cannot publish stale evidence.
        if (
            record.status == "ready"
            or record.job_id != job_id
            or record.processing_token != token
            or job.status != "running"
            or job.lease_token != token
            or job.lease_until is None
            or job.lease_until <= now
        ):
            return
        will_retry = bool(
            failure and failure.status == 502 and attempt < 3 and job.attempt < job.max_attempts
        )
        if failure:
            # Pending automatic retries remain pollable; failed means a terminal attempt.
            record.status = "uploaded" if will_retry else "failed"
            record.error = {"code": failure.code, "message": failure.message, "details": None}
        else:
            for ordinal, unit in enumerate(result.units):
                session.add(
                    StoredSourceUnit(document_id=document_id, ordinal=ordinal, **unit.model_dump())
                )
            record.page_count = result.page_count
            record.warnings = record.warnings + [
                warning.model_dump(mode="json", by_alias=True) for warning in result.warnings
            ]
            record.status, record.error = "ready", None
    duration = round((time.monotonic() - started) * 1000)
    if failure:
        log(
            "document.failed",
            level=logging.ERROR,
            documentId=document_id,
            jobId=job_id,
            attempt=attempt,
            durationMs=duration,
            errorCode=failure.code,
            exc_info=failure_trace or False,
        )
        if will_retry:
            raise failure
    else:
        log(
            "document.ready",
            documentId=document_id,
            jobId=job_id,
            attempt=attempt,
            durationMs=duration,
        )
