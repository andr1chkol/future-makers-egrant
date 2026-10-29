from datetime import timedelta
from uuid import uuid4

from app.platform.jobs import JobPayload, JobRegistry, claim, enqueue, run_once
from app.platform.logging import request_id
from app.platform.models import Job
from app.worker import build_registry
from sqlalchemy import func, select, text, update


def test_migration_and_transactional_enqueue(database):
    with database() as session:
        assert session.scalar(text("SELECT version_num FROM alembic_version")) == "0001_platform"
        assert session.scalar(text("SHOW server_version")).startswith("16.")
        enqueue(session, "document.process", JobPayload(resource_id=uuid4()))
        session.rollback()
        assert session.scalar(select(func.count()).select_from(Job)) == 0


def test_claim_skip_locked_and_crash_recovery(database):
    with database.begin() as session:
        first = enqueue(session, "document.process", JobPayload(resource_id=uuid4()))
        second = enqueue(session, "document.process", JobPayload(resource_id=uuid4()))
    with database.begin() as one:
        a = claim(one)
        with database.begin() as two:
            b = claim(two)
            assert a.id != b.id
            assert {a.id, b.id} == {first, second}
    with database.begin() as session:
        job = session.get(Job, first)
        old_token = job.lease_token
        job.lease_until = session.scalar(select(func.now())) - timedelta(seconds=1)
    with database.begin() as session:
        recovered = claim(session)
        assert recovered.id == first
        assert recovered.attempt == 2
        assert recovered.lease_token != old_token
        result = session.execute(
            update(Job).where(Job.id == first, Job.lease_token == old_token).values(status="done")
        )
        assert result.rowcount == 0


def test_retry_is_bounded_and_request_correlation_reaches_handler(database):
    correlation, resource_id = str(uuid4()), uuid4()
    token = request_id.set(correlation)
    try:
        with database.begin() as session:
            job_id = enqueue(session, "extraction.process", JobPayload(resource_id=resource_id))
    finally:
        request_id.reset(token)
    registry = JobRegistry()
    observed = []

    def failing(session, id):
        observed.append((id, request_id.get()))
        raise RuntimeError("private provider response")

    registry.register_handler("extraction.process", failing)
    for attempt in range(1, 4):
        assert run_once(database, registry)
        with database.begin() as session:
            job = session.get(Job, job_id)
            assert job.attempt == attempt
            assert job.status == ("failed" if attempt == 3 else "queued")
            job.available_at = session.scalar(select(func.now())) - timedelta(seconds=1)
    assert not run_once(database, registry)
    assert observed == [(resource_id, correlation)] * 3


def test_missing_handlers_fail_and_apply_is_never_blindly_retried(database):
    registry = build_registry()
    assert set(registry.handlers) == {"document.process", "extraction.process", "submission.apply"}
    with database.begin() as session:
        job_id = enqueue(session, "submission.apply", JobPayload(resource_id=uuid4()))
    assert run_once(database, registry)
    with database() as session:
        job = session.get(Job, job_id)
        assert job.status == "failed"
        assert job.max_attempts == 1
        assert job.error_code == "HANDLER_UNAVAILABLE"
    assert not run_once(database, registry)


def test_success_and_expired_exhausted_job(database):
    registry = JobRegistry()
    seen = []
    registry.register_handler("document.process", lambda session, id: seen.append(id))
    resource_id = uuid4()
    with database.begin() as session:
        job_id = enqueue(session, "document.process", JobPayload(resource_id=resource_id))
    assert run_once(database, registry)
    assert seen == [resource_id]
    with database() as session:
        assert session.get(Job, job_id).status == "done"
    with database.begin() as session:
        apply_id = enqueue(session, "submission.apply", JobPayload(resource_id=uuid4()))
        assert claim(session).id == apply_id
    with database.begin() as session:
        session.get(Job, apply_id).lease_until = session.scalar(select(func.now())) - timedelta(
            seconds=1
        )
    with database.begin() as session:
        assert claim(session) is None
        assert session.get(Job, apply_id).status == "failed"
        assert session.get(Job, apply_id).error_code == "LEASE_EXHAUSTED"


def test_late_worker_cannot_finish_after_lease_reclaimed(database):
    registry = JobRegistry()
    with database.begin() as session:
        job_id = enqueue(session, "document.process", JobPayload(resource_id=uuid4()))
    replacement_tokens = []

    def slow_handler(session, id):
        with database.begin() as concurrent:
            concurrent.get(Job, job_id).lease_until = concurrent.scalar(
                select(func.now())
            ) - timedelta(seconds=1)
        with database.begin() as concurrent:
            replacement_tokens.append(claim(concurrent).lease_token)

    registry.register_handler("document.process", slow_handler)
    assert run_once(database, registry)
    with database() as session:
        job = session.get(Job, job_id)
        assert job.status == "running"
        assert job.attempt == 2
        assert job.lease_token == replacement_tokens[0]
