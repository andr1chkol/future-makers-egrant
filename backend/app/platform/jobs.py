"""At-least-once jobs. A lease token fences completion by an expired worker."""

import logging
from collections.abc import Callable
from datetime import timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.platform.contracts import JobKind
from app.platform.logging import log, request_id
from app.platform.models import Job


class JobPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_id: UUID


class HandlerUnavailableError(Exception):
    pass


Handler = Callable[[Session, UUID], None]


class JobRegistry:
    def __init__(self):
        self.handlers: dict[str, Handler] = {}

    def register_handler(self, kind: JobKind, handler: Handler) -> None:
        if kind in self.handlers:
            raise ValueError("Job handler already registered")
        self.handlers[kind] = handler


def enqueue(session: Session, kind: JobKind, payload: JobPayload) -> UUID:
    if kind not in {"document.process", "extraction.process", "submission.apply"}:
        raise ValueError("Unknown job kind")
    job = Job(
        id=uuid4(),
        kind=kind,
        payload=payload.model_dump(mode="json"),
        request_id=UUID(request_id.get()) if request_id.get() else None,
        max_attempts=1 if kind == "submission.apply" else 3,
    )
    session.add(job)
    session.flush()
    return job.id


def claim(session: Session, lease_seconds: int = 60) -> Job | None:
    if not 1 <= lease_seconds <= 3600:
        raise ValueError("Invalid lease duration")
    eligible = or_(
        and_(Job.status == "queued", Job.available_at <= func.now()),
        and_(Job.status == "running", Job.lease_until < func.now()),
    )
    # Exhausted leases are terminal. Submission effects must be reconciled by their owner.
    session.execute(
        update(Job)
        .where(eligible, Job.attempt >= Job.max_attempts)
        .values(status="failed", error_code="LEASE_EXHAUSTED", lease_token=None, lease_until=None)
    )
    job = session.scalar(
        select(Job)
        .where(eligible, Job.attempt < Job.max_attempts)
        .order_by(Job.available_at, Job.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job:
        job.status = "running"
        job.attempt += 1
        job.lease_token = uuid4()
        job.lease_until = session.scalar(select(func.now())) + timedelta(seconds=lease_seconds)
        session.flush()
    return job


def run_once(factory: sessionmaker[Session], registry: JobRegistry) -> bool:
    with factory.begin() as session:
        job = claim(session)
        if not job:
            return False
        job_id, lease_token = job.id, job.lease_token
        kind, payload, attempt, max_attempts = job.kind, job.payload, job.attempt, job.max_attempts
        correlation = str(job.request_id) if job.request_id else None
    context_token = request_id.set(correlation)
    try:
        handler = registry.handlers.get(kind)
        if handler is None:
            raise HandlerUnavailableError("Handler not registered")
        # Handlers own short transactions; provider calls must not hold database locks.
        with factory() as session:
            handler(session, JobPayload.model_validate(payload).resource_id)
        status, error_code = "done", None
    except Exception as error:
        terminal = isinstance(error, HandlerUnavailableError) or attempt >= max_attempts
        status = "failed" if terminal else "queued"
        error_code = (
            "HANDLER_UNAVAILABLE" if isinstance(error, HandlerUnavailableError) else "JOB_FAILED"
        )
        log(
            "job.failed" if terminal else "job.retry_scheduled",
            level=logging.ERROR if terminal else logging.WARNING,
            jobId=job_id,
            attempt=attempt,
            errorCode=error_code,
            exc_info=True,
        )
    try:
        with factory.begin() as session:
            result = session.execute(
                update(Job)
                .where(
                    Job.id == job_id, Job.lease_token == lease_token, Job.lease_until > func.now()
                )
                .values(
                    status=status,
                    error_code=error_code,
                    lease_token=None,
                    lease_until=None,
                    available_at=func.now() + timedelta(seconds=min(2**attempt, 60)),
                )
            )
        if result.rowcount and status == "done":
            log("job.completed", jobId=job_id, attempt=attempt)
    finally:
        request_id.reset(context_token)
    return True
