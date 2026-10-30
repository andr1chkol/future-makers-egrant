"""Recovery of runs whose extraction.process job ended without a stored outcome."""

import json
import threading
from datetime import timedelta
from uuid import uuid4

from app.extraction import service
from app.extraction.models import ExtractionRecord
from app.extraction.service import (
    create_extractions,
    get_extraction,
    process_extraction,
    recover_terminal_extractions,
    retry_extraction,
)
from app.platform.contracts import CreateExtractions
from app.platform.jobs import claim
from app.platform.logging import request_id
from app.platform.models import Job
from extraction_support import (
    ScriptedProvider,
    example_document,
    example_profile,
    money,
    reply_for,
    value,
)
from sqlalchemy import func, select, text, update

PROFILE = example_profile()
DOCUMENT = example_document()


def good_reply():
    return reply_for(
        PROFILE,
        {
            "supplier": value("Demo Paper s.r.o.", "row-2"),
            "buyer": value("Demo Grant Association", "row-2"),
            "total": money("55.00", "EUR", "row-4", "55.00"),
        },
    )


def create(database):
    request = CreateExtractions(
        document_ids=[DOCUMENT.document_id], profile_id=PROFILE.id, profile_version=1
    )
    with database() as session:
        (queued,) = create_extractions(session, request).extractions
    return queued.id


def read(database, id):
    with database() as session:
        return get_extraction(session, id)


def record(database, id):
    with database() as session:
        return session.get(ExtractionRecord, id)


def sweep(database):
    with database() as session:
        recover_terminal_extractions(session)


def strand(database, id, status, attempt=3, error_code="LEASE_EXHAUSTED"):
    """Leave a run the way the platform does after its job gave up for good."""
    with database.begin() as session:
        session.execute(
            update(ExtractionRecord)
            .where(ExtractionRecord.id == id)
            .values(
                status=status, attempt=attempt, run_token=uuid4() if status == "running" else None
            )
        )
        session.execute(
            update(Job)
            .where(Job.payload["resource_id"].astext == str(id))
            .values(status="failed", attempt=3, error_code=error_code, lease_token=None)
        )


def test_crash_on_the_final_lease_fails_the_run(database, modules):
    extraction_id = create(database)
    # Attempt 3 claimed the run, then the worker died: the job lease expires while running.
    with database.begin() as session:
        session.execute(
            update(Job).values(
                status="running",
                attempt=3,
                lease_token=uuid4(),
                lease_until=func.now() - timedelta(seconds=1),
            )
        )
        session.execute(
            update(ExtractionRecord).values(status="running", attempt=3, run_token=uuid4())
        )
    with database.begin() as session:
        assert claim(session) is None  # the platform turns the exhausted lease into a failed job
    sweep(database)
    stored = record(database, extraction_id)
    assert (stored.status, stored.run_token, stored.attempt) == ("failed", None, 3)
    assert read(database, extraction_id).error.code == "EXTRACTION_INTERRUPTED"


def test_run_requeued_on_the_queue_final_attempt_is_failed(database, modules):
    # The run's own count lagged behind the job's, so the handler re-queued it and
    # raised on the job's last attempt.
    extraction_id = create(database)
    strand(database, extraction_id, "queued", attempt=2, error_code="JOB_FAILED")
    sweep(database)
    stored = record(database, extraction_id)
    assert (stored.status, stored.attempt) == ("failed", 2)


def test_a_newer_active_retry_is_left_alone(database, modules):
    extraction_id = create(database)
    strand(database, extraction_id, "queued")
    with database.begin() as session:
        session.execute(
            update(ExtractionRecord)
            .where(ExtractionRecord.id == extraction_id)
            .values(updated_at=func.now() - timedelta(minutes=6))
        )
    with database() as session:
        retry_extraction(session, extraction_id)
    sweep(database)
    assert record(database, extraction_id).status == "queued"
    with database() as session:
        statuses = session.scalars(select(Job.status).order_by(Job.created_at)).all()
    assert statuses == ["failed", "queued"]


def test_finished_runs_are_untouched(database, modules):
    extraction_id = create(database)
    process_extraction_with(database, extraction_id, ScriptedProvider(good_reply()))
    before = read(database, extraction_id)
    with database.begin() as session:
        session.execute(update(Job).values(status="failed", error_code="LEASE_EXHAUSTED"))
    sweep(database)
    assert read(database, extraction_id) == before


def test_recovery_skips_a_run_locked_by_a_concurrent_retry(database, modules):
    extraction_id = create(database)
    strand(database, extraction_id, "running")
    with database() as holder:
        # Stands in for retry_extraction holding the row lock.
        holder.execute(
            text("SELECT id FROM extractions WHERE id = :id FOR UPDATE"), {"id": extraction_id}
        )
        sweep(database)
        assert record(database, extraction_id).status == "running"
        holder.rollback()
    sweep(database)
    assert record(database, extraction_id).status == "failed"
    # A failed run can then be retried, and the sweep leaves the new job alone.
    with database() as session:
        assert retry_extraction(session, extraction_id).status == "queued"
    sweep(database)
    assert record(database, extraction_id).status == "queued"


def test_a_late_worker_cannot_overwrite_a_recovered_run(database, modules):
    extraction_id = create(database)
    claimed = threading.Event()
    release = threading.Event()

    class SlowProvider(ScriptedProvider):
        def extract(self, profile, options, document):
            claimed.set()
            release.wait(timeout=10)
            return json.dumps(good_reply())

    worker = threading.Thread(
        target=process_extraction_with, args=(database, extraction_id, SlowProvider())
    )
    worker.start()
    assert claimed.wait(timeout=10)
    with database.begin() as session:
        session.execute(update(Job).values(status="failed", error_code="LEASE_EXHAUSTED"))
    sweep(database)
    release.set()
    worker.join(timeout=10)
    result = read(database, extraction_id)
    assert (result.status, result.error.code, result.fields) == (
        "failed",
        "EXTRACTION_INTERRUPTED",
        [],
    )


def test_repeat_recovery_changes_nothing(database, modules, captured_logs):
    extraction_id = create(database)
    strand(database, extraction_id, "running")
    sweep(database)
    first = read(database, extraction_id)
    sweep(database)
    assert read(database, extraction_id) == first
    assert [r["event"] for r in captured_logs()].count("extraction.failed") == 1


def test_recovery_is_bounded_per_sweep(database, modules, monkeypatch):
    first, second = create(database), create(database)
    strand(database, first, "running")
    strand(database, second, "queued")
    monkeypatch.setattr(service, "RECOVERY_BATCH_SIZE", 1)
    sweep(database)
    assert sorted(record(database, id).status for id in (first, second)) == ["failed", "queued"]
    sweep(database)
    assert {record(database, id).status for id in (first, second)} == {"failed"}


def test_recovery_logs_original_correlation_without_document_data(database, modules, captured_logs):
    correlation = str(uuid4())
    token = request_id.set(correlation)
    try:
        extraction_id = create(database)
    finally:
        request_id.reset(token)
    strand(database, extraction_id, "running")
    with database() as session:
        job = session.scalar(select(Job))
    sweep(database)
    (failed,) = [r for r in captured_logs() if r["event"] == "extraction.failed"]
    assert failed["level"] == "ERROR"
    assert failed["errorCode"] == "EXTRACTION_INTERRUPTED"
    assert failed["requestId"] == correlation
    assert failed["jobId"] == str(job.id)
    assert failed["extractionId"] == str(extraction_id)
    assert failed["documentId"] == str(DOCUMENT.document_id)
    assert failed["attempt"] == 3
    logged = captured_logs.text()
    assert all(unit.text not in logged for unit in DOCUMENT.units)


def process_extraction_with(database, id, provider):
    with database() as session:
        process_extraction(session, id, provider=provider)
