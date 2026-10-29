import json
import logging
import time
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import String, cast, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.integrations import dependencies
from app.integrations.models import SubmissionRecord
from app.integrations.payload import build_submission_payload
from app.platform.contracts import CreateSubmission, Submission, SubmissionPayload
from app.platform.errors import ConflictError, NotFoundError, UnavailableError, ValidationError
from app.platform.logging import log
from app.platform.models import Job


def submission_dto(record: SubmissionRecord) -> Submission:
    return Submission.model_validate(
        {name: getattr(record, name) for name in Submission.model_fields}
    )


def create_submission(
    session: Session,
    request: CreateSubmission,
    idempotency_key: str,
) -> Submission:
    """Persist an immutable payload atomically; retries reuse the original operation."""
    if not 1 <= len(idempotency_key) <= 128:
        raise ValidationError()
    request_hash = sha256(
        json.dumps(
            request.model_dump(mode="json", by_alias=True),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    start = time.monotonic()
    created = False
    with session.begin():
        record = session.scalar(
            select(SubmissionRecord).where(SubmissionRecord.idempotency_key == idempotency_key)
        )
        if record is None:
            # There is no documented application-data write interface or reconciliation API.
            # Even configured credentials must not enable an invented eGrant operation.
            if request.mode == "egrant":
                raise UnavailableError()
            review = dependencies.get_confirmed_review(
                session, request.review_id, request.review_revision
            )
            if (
                review.extraction_id != request.review_id
                or review.revision != request.review_revision
            ):
                raise ConflictError()
            extraction = dependencies.get_extraction(session, request.review_id)
            profile = dependencies.get_profile(
                session, extraction.profile_id, extraction.profile_version
            )
            form = dependencies.get_form(session, profile.form_id)
            payload = build_submission_payload(review, extraction, profile, form)
            # ON CONFLICT waits for a concurrent insert to commit. The next statement
            # sees its row at READ COMMITTED; no failed transaction or duplicate operation.
            created_id = session.scalar(
                insert(SubmissionRecord)
                .values(
                    id=uuid4(),
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    review_id=request.review_id,
                    review_revision=request.review_revision,
                    mode=request.mode,
                    target_context=request.target_context.model_dump(mode="json", by_alias=True),
                    status="prepared",
                    payload=payload.model_dump(mode="json", by_alias=True),
                    external_receipt=None,
                    error=None,
                )
                .on_conflict_do_nothing(index_elements=[SubmissionRecord.idempotency_key])
                .returning(SubmissionRecord.id)
            )
            created = created_id is not None
            record = session.scalar(
                select(SubmissionRecord).where(SubmissionRecord.idempotency_key == idempotency_key)
            )
        if record.request_hash != request_hash:
            raise ConflictError()
        result = submission_dto(record)
    if created:
        log(
            "submission.prepared",
            submissionId=result.id,
            extractionId=result.review_id,
            durationMs=round((time.monotonic() - start) * 1000),
        )
    return result


def get_submission(session: Session, id: UUID) -> Submission:
    record = session.get(SubmissionRecord, id)
    if record is None:
        raise NotFoundError()
    return submission_dto(record)


def export_submission(session: Session, id: UUID) -> SubmissionPayload:
    with session.begin():
        record = session.scalar(
            select(SubmissionRecord).where(SubmissionRecord.id == id).with_for_update()
        )
        if record is None:
            raise NotFoundError()
        if record.mode != "export" or record.status not in {"prepared", "exported"}:
            raise ConflictError()
        record.status = "exported"
        return submission_dto(record).payload


def apply_submission(session: Session, id: UUID) -> None:
    """No external writes are enabled. Preserve uncertainty from any interrupted apply."""
    with session.begin():
        record = session.scalar(
            select(SubmissionRecord).where(SubmissionRecord.id == id).with_for_update()
        )
        if record is None:
            raise NotFoundError()
        if record.mode != "egrant" or record.status in {"applied", "failed", "unknown"}:
            return
        # An applying operation may already have affected the remote application.
        # Never enqueue or repeat it without receipt/current-state reconciliation.
        record.status = "unknown" if record.status == "applying" else "failed"
        record.error = {
            "code": "RECONCILIATION_REQUIRED"
            if record.status == "unknown"
            else "FEATURE_UNAVAILABLE",
            "message": "External reconciliation required"
            if record.status == "unknown"
            else "eGrant adapter unavailable",
            "details": None,
        }
        result = submission_dto(record)
    log(
        f"submission.{result.status}",
        level=logging.ERROR,
        submissionId=result.id,
        extractionId=result.review_id,
        errorCode=result.error.code,
    )


def recover_interrupted_submissions(session: Session) -> None:
    """Terminal queue leases must not leave an operation apparently in progress."""
    with session.begin():
        records = session.scalars(
            select(SubmissionRecord)
            .where(
                SubmissionRecord.mode == "egrant",
                SubmissionRecord.status.in_(["prepared", "applying"]),
                select(Job.id)
                .where(
                    Job.kind == "submission.apply",
                    Job.status == "failed",
                    Job.payload["resource_id"].astext == cast(SubmissionRecord.id, String),
                )
                .exists(),
            )
            .with_for_update(skip_locked=True)
            .limit(100)
        ).all()
        for record in records:
            record.status = "unknown" if record.status == "applying" else "failed"
            record.error = {
                "code": "RECONCILIATION_REQUIRED"
                if record.status == "unknown"
                else "APPLY_NOT_STARTED",
                "message": "External reconciliation required"
                if record.status == "unknown"
                else "Apply job exhausted before dispatch",
                "details": None,
            }
        results = [submission_dto(record) for record in records]
    for result in results:
        log(
            f"submission.{result.status}",
            level=logging.ERROR,
            submissionId=result.id,
            extractionId=result.review_id,
            errorCode=result.error.code,
        )
