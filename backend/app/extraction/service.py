"""Extraction lifecycle: creation, worker processing, retries and reads.

Processing runs in three phases so that the provider call never holds a
database transaction or row lock: claim the run, call the provider, then
persist under the run token. A worker whose lease expired mid-call finds its
token replaced and discards its result instead of overwriting a newer run.
"""

import logging
import time
from datetime import UTC, timedelta
from uuid import UUID, uuid4

from sqlalchemy import String, cast, func, select, update
from sqlalchemy.orm import Session

from app.extraction.assembly import assemble_extraction
from app.extraction.models import ExtractionRecord
from app.extraction.providers import (
    ExtractionProvider,
    FixtureProvider,
    OpenAIProvider,
    ProviderError,
)
from app.extraction.schema import (
    OptionKeys,
    ProviderOutputError,
    option_scope,
    parse_provider_output,
)
from app.platform.contracts import (
    CreateExtractions,
    DomainErrorDTO,
    Extraction,
    ExtractionBatch,
    FormDefinition,
    NormalizedDocument,
    Profile,
    QueuedExtraction,
)
from app.platform.errors import ConflictError, DomainError, NotFoundError, ValidationError
from app.platform.jobs import JobPayload, enqueue
from app.platform.logging import log
from app.platform.models import Job
from app.platform.settings import get_settings

# Matches the platform's attempt limit for extraction.process jobs.
MAX_ATTEMPTS = 3
# Three 60-second leases plus the 2 s and 4 s backoffs take a little over three
# minutes. A queued or running run untouched for longer has lost its job: the
# worker died on the last attempt, or a rolled-back claim let the job's attempt
# count run ahead of the run's. Such runs may be retried like failed ones.
STALE_AFTER = timedelta(minutes=5)
# Runs examined per recovery sweep; the worker calls the sweep on every polling cycle.
RECOVERY_BATCH_SIZE = 50

FAILURE_MESSAGES = {
    "AI_TIMEOUT": "The AI provider did not answer in time",
    "AI_RATE_LIMITED": "The AI provider rate limit was reached",
    "AI_UNREACHABLE": "The AI provider could not be reached",
    "AI_UPSTREAM_ERROR": "The AI provider returned an error",
    "AI_OUTPUT_INVALID": "The AI provider returned output that does not match the profile",
    "AI_REFUSED": "The AI provider refused to process the document",
    "AI_AUTH_FAILED": "The AI provider rejected the configured credentials",
    "AI_REQUEST_REJECTED": "The AI provider rejected the request",
    "AI_NOT_CONFIGURED": "The AI provider is not configured",
    "DOCUMENT_TOO_LARGE": "The document is too large to extract in one request",
    "DOCUMENT_UNAVAILABLE": "The document is no longer available for extraction",
    "FIXTURE_NOT_AVAILABLE": "Fixture mode has no recorded result for this document and profile",
    "EXTRACTION_INTERNAL_ERROR": "Extraction failed unexpectedly",
    "EXTRACTION_INTERRUPTED": "Processing stopped before a result was stored",
}


class AINotConfiguredError(DomainError):
    def __init__(self):
        super().__init__("AI_NOT_CONFIGURED", 503, FAILURE_MESSAGES["AI_NOT_CONFIGURED"])


class ExtractionRetryScheduled(Exception):
    """Tells the platform worker to retry the job; the extraction is queued again."""


# Documents and profiles are separate modules assembled by member 5. Importing at
# call time keeps this module importable on its own branch and lets tests
# substitute their public functions.
def load_normalized(session: Session, document_id: UUID) -> NormalizedDocument:
    from app.documents.service import get_normalized

    return get_normalized(session, document_id)


def load_profile(session: Session, profile_id: UUID, version: int) -> Profile:
    from app.profiles.service import get_profile

    return get_profile(session, profile_id, version)


def load_form(session: Session, form_id: UUID) -> FormDefinition:
    from app.profiles.service import get_form

    return get_form(session, form_id)


def provider_for(mode: str) -> ExtractionProvider | None:
    if mode == "fixture":
        return FixtureProvider()
    return OpenAIProvider.from_settings(get_settings())


def form_option_keys(profile: Profile, form: FormDefinition) -> OptionKeys:
    """Collect permitted option keys for the profile's string targets."""
    fields = {field.tag: field for field in form.fields}
    tables = {table.tag: {column.tag: column for column in table.columns} for table in form.tables}
    options: OptionKeys = {}
    for spec in profile.scalar_fields:
        target = fields.get(spec.target_tag)
        if spec.type == "string" and target and target.options:
            options[option_scope(spec.key)] = [option.key for option in target.options]
    for table in profile.table_fields:
        columns = tables.get(table.target_tag, {})
        for spec in table.columns:
            target = columns.get(spec.target_tag)
            if spec.type == "string" and target and target.options:
                options[option_scope(spec.key, table.key)] = [
                    option.key for option in target.options
                ]
    return options


def create_extractions(session: Session, request: CreateExtractions) -> ExtractionBatch:
    """Create one queued extraction per document, each with its own job.

    Raises NotFoundError for an unknown profile or document, ConflictError when a
    document is not ready yet, ValidationError for repeated document IDs and
    AINotConfiguredError in live mode without provider settings.
    """
    if len(set(request.document_ids)) != len(request.document_ids):
        raise ValidationError()
    mode = get_settings().app_mode
    if provider_for(mode) is None:
        raise AINotConfiguredError()
    with session.begin():
        profile = load_profile(session, request.profile_id, request.profile_version)
        if profile.version != request.profile_version:
            raise NotFoundError()
        options = form_option_keys(profile, load_form(session, profile.form_id))
        records = []
        for document_id in request.document_ids:
            # Fails early with 404/409 instead of queueing work that cannot start.
            load_normalized(session, document_id)
            record = ExtractionRecord(
                id=uuid4(),
                document_id=document_id,
                profile_id=profile.id,
                profile_version=profile.version,
                profile_snapshot=profile.model_dump(mode="json", by_alias=True),
                option_keys=options,
                mode=mode,
                status="queued",
                attempt=0,
                fields=[],
                tables=[],
                warnings=[],
            )
            session.add(record)
            records.append(record)
        session.flush()
        for record in records:
            enqueue(session, "extraction.process", JobPayload(resource_id=record.id))
    return ExtractionBatch(
        extractions=[
            QueuedExtraction(id=record.id, document_id=record.document_id, status=record.status)
            for record in records
        ]
    )


def get_extraction(session: Session, id: UUID) -> Extraction:
    record = session.get(ExtractionRecord, id)
    if record is None:
        raise NotFoundError()
    return to_dto(record)


def list_extractions(session: Session, limit: int, offset: int) -> tuple[list[Extraction], int]:
    total = session.scalar(select(func.count()).select_from(ExtractionRecord))
    records = session.scalars(
        select(ExtractionRecord)
        .order_by(ExtractionRecord.created_at.desc(), ExtractionRecord.id)
        .limit(limit)
        .offset(offset)
    )
    return [to_dto(record) for record in records], total


def retry_extraction(session: Session, id: UUID) -> Extraction:
    """Queue a failed or stale extraction again under the same ID.

    Failed runs and runs left queued or running past STALE_AFTER qualify. None
    of them produced a result, so no review can exist and nothing a person
    entered is lost. If the old job does come back, the run token keeps it from
    overwriting the new attempt, and a finished run makes later jobs no-ops.
    """
    with session.begin():
        record = session.get(ExtractionRecord, id, with_for_update=True)
        if record is None:
            raise NotFoundError()
        stale = record.status in {"queued", "running"} and record.updated_at < session.scalar(
            select(func.now() - STALE_AFTER)
        )
        if record.status != "failed" and not stale:
            raise ConflictError()
        if provider_for(record.mode) is None:
            raise AINotConfiguredError()
        record.status, record.attempt, record.error = "queued", 0, None
        record.run_token = None
        enqueue(session, "extraction.process", JobPayload(resource_id=record.id))
        session.flush()
        session.refresh(record)
        return to_dto(record)


def recover_terminal_extractions(session: Session) -> None:
    """Fail runs left queued or running after their job ended for good.

    The platform fails a job without calling the handler when its last lease
    expires, and after the handler raised on the queue's last attempt. Either way
    the run keeps its queued or running status with nothing left to process it.
    The member 5 worker calls this sweep on every polling cycle with a fresh
    session.

    A run is failed only when none of its extraction.process jobs is queued or
    running and the latest one has failed. A newer manual retry is therefore left
    alone. The attempt count is kept and no job is enqueued, so recovery never
    starts another paid provider call. Clearing the run token fences a worker that
    is still waiting on the provider.
    """
    recovered = []
    same_run = (Job.kind == "extraction.process") & (
        Job.payload["resource_id"].astext == cast(ExtractionRecord.id, String)
    )
    active_job = select(Job.id).where(same_run, Job.status.in_(("queued", "running"))).exists()
    latest_status = (
        select(Job.status)
        .where(same_run)
        .order_by(Job.created_at.desc(), Job.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    with session.begin():
        records = session.scalars(
            select(ExtractionRecord)
            # Filter before LIMIT: active runs must not consume every sweep slot.
            .where(
                ExtractionRecord.status.in_(("queued", "running")),
                ~active_job,
                latest_status == "failed",
            )
            .order_by(ExtractionRecord.updated_at, ExtractionRecord.id)
            .limit(RECOVERY_BATCH_SIZE)
            .with_for_update(skip_locked=True)
        ).all()
        jobs = jobs_by_extraction(session, [record.id for record in records])
        error = DomainErrorDTO(
            code="EXTRACTION_INTERRUPTED", message=FAILURE_MESSAGES["EXTRACTION_INTERRUPTED"]
        ).model_dump(mode="json", by_alias=True)
        for record in records:
            history = jobs.get(record.id, [])
            if not history or any(job.status in {"queued", "running"} for job in history):
                continue
            latest = history[-1]
            if latest.status != "failed":
                continue
            record.status, record.run_token, record.error = "failed", None, error
            recovered.append((record.id, record.document_id, latest))
    for extraction_id, document_id, job in recovered:
        correlation = {"requestId": job.request_id} if job.request_id else {}
        log(
            "extraction.failed",
            level=logging.ERROR,
            errorCode="EXTRACTION_INTERRUPTED",
            extractionId=extraction_id,
            documentId=document_id,
            jobId=job.id,
            attempt=job.attempt,
            **correlation,
        )


def jobs_by_extraction(session: Session, ids: list[UUID]) -> dict[UUID, list[Job]]:
    """Each run's extraction.process jobs, oldest first."""
    if not ids:
        return {}
    jobs = session.scalars(
        select(Job)
        .where(
            Job.kind == "extraction.process",
            Job.payload["resource_id"].astext.in_([str(id) for id in ids]),
        )
        .order_by(Job.created_at, Job.id)
    )
    history: dict[UUID, list[Job]] = {}
    for job in jobs:
        history.setdefault(UUID(job.payload["resource_id"]), []).append(job)
    return history


def process_extraction(
    session: Session, id: UUID, provider: ExtractionProvider | None = None
) -> None:
    """Run one attempt of the extraction.process job.

    Safe to execute more than once: finished runs are left untouched and only
    the most recent claim may write a result. Transient provider failures are
    re-queued until MAX_ATTEMPTS by raising ExtractionRetryScheduled; every other
    outcome is persisted here, so the job itself completes normally.
    """
    started = time.monotonic()
    with session.begin():
        record = session.get(ExtractionRecord, id, with_for_update=True)
        if record is None:
            raise NotFoundError()
        if record.status in {"ready", "failed"}:
            return
        record.status, record.attempt, record.run_token = "running", record.attempt + 1, uuid4()
        run_token, attempt, mode = record.run_token, record.attempt, record.mode
        document_id = record.document_id
        profile = Profile.model_validate(record.profile_snapshot)
        options: OptionKeys = record.option_keys
        try:
            document = load_normalized(session, document_id)
        except (NotFoundError, ConflictError):
            document = None
    context = {"extractionId": id, "documentId": document_id, "attempt": attempt}
    log("extraction.started", **context)
    if document is None:
        fail(session, id, run_token, "DOCUMENT_UNAVAILABLE", started, context)
        return

    unexpected: Exception | None = None
    try:
        provider = provider or provider_for(mode)
        if provider is None:
            raise ProviderError("AI_NOT_CONFIGURED", retryable=False)
        if provider.mode != mode:
            # A fixture must never answer for a live run, nor the reverse.
            raise ProviderError("AI_NOT_CONFIGURED", retryable=False)
        raw = parse_provider_output(provider.extract(profile, options, document), profile)
        result = assemble_extraction(raw, profile, document, options)
    except ProviderOutputError:
        failure = ProviderError("AI_OUTPUT_INVALID", retryable=True)
    except ProviderError as error:
        failure = error
    except Exception as error:
        # Kept for the log stack only; exception text may contain document data.
        unexpected = error
        failure = ProviderError("EXTRACTION_INTERNAL_ERROR", retryable=True)
    else:
        failure = None

    if failure is not None:
        if failure.retryable and attempt < MAX_ATTEMPTS:
            with session.begin():
                requeued = session.execute(
                    claimed(id, run_token).values(status="queued", run_token=None)
                ).rowcount
            if requeued:
                log(
                    "job.retry_scheduled",
                    level=logging.WARNING,
                    errorCode=failure.code,
                    exc_info=unexpected or False,
                    **context,
                )
                raise ExtractionRetryScheduled(failure.code)
            return
        fail(session, id, run_token, failure.code, started, context, unexpected)
        return

    with session.begin():
        stored = session.execute(
            claimed(id, run_token).values(
                status="ready",
                run_token=None,
                error=None,
                fields=[field.model_dump(mode="json", by_alias=True) for field in result.fields],
                tables=[table.model_dump(mode="json", by_alias=True) for table in result.tables],
                warnings=[item.model_dump(mode="json", by_alias=True) for item in result.warnings],
            )
        ).rowcount
    if not stored:
        return
    for code in sorted({item.code for item in result.warnings}):
        log("extraction.validation_warning", level=logging.WARNING, errorCode=code, **context)
    log("extraction.ready", durationMs=elapsed_ms(started), **context)


def claimed(id: UUID, run_token: UUID):
    return update(ExtractionRecord).where(
        ExtractionRecord.id == id,
        ExtractionRecord.run_token == run_token,
        ExtractionRecord.status == "running",
    )


def fail(
    session: Session,
    id: UUID,
    run_token: UUID,
    code: str,
    started: float,
    context: dict,
    unexpected: Exception | None = None,
) -> None:
    error = DomainErrorDTO(code=code, message=FAILURE_MESSAGES[code])
    with session.begin():
        stored = session.execute(
            claimed(id, run_token).values(
                status="failed", run_token=None, error=error.model_dump(mode="json", by_alias=True)
            )
        ).rowcount
    if stored:
        log(
            "extraction.failed",
            level=logging.ERROR,
            errorCode=code,
            durationMs=elapsed_ms(started),
            exc_info=unexpected or False,
            **context,
        )


def elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


def to_dto(record: ExtractionRecord) -> Extraction:
    return Extraction.model_validate(
        {
            "id": record.id,
            "documentId": record.document_id,
            "profileId": record.profile_id,
            "profileVersion": record.profile_version,
            "status": record.status,
            "mode": record.mode,
            "fields": record.fields,
            "tables": record.tables,
            "warnings": record.warnings,
            "error": record.error,
            "createdAt": record.created_at.astimezone(UTC),
        }
    )
