import io
import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.integrations import service
from app.integrations.models import SubmissionRecord
from app.platform.contracts import Submission
from app.platform.jobs import JobPayload, claim, enqueue, run_once
from app.platform.logging import JsonFormatter, logger, request_id
from app.platform.models import Job
from app.worker import build_registry
from sqlalchemy import select

from .test_submissions import EXAMPLES


def seed_apply(database, status):
    sample = Submission.model_validate_json((EXAMPLES / "submission.json").read_text())
    values = sample.model_dump(mode="python")
    values.update(id=uuid4(), mode="egrant", status=status)
    for name in ["payload", "target_context"]:
        values[name] = getattr(sample, name).model_dump(mode="json", by_alias=True)
    with database.begin() as session:
        record = SubmissionRecord(**values, idempotency_key=str(uuid4()), request_hash="0" * 64)
        session.add(record)
        session.flush()
        job = enqueue(session, "submission.apply", JobPayload(resource_id=record.id))
    return record.id, job


@pytest.mark.parametrize("status,expected", [("applying", "unknown"), ("prepared", "failed")])
def test_worker_never_repeats_an_external_write(database, status, expected):
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    correlation = str(uuid4())
    token = request_id.set(correlation)
    try:
        id, job_id = seed_apply(database, status)
        assert run_once(database, build_registry())
        assert not run_once(database, build_registry())
        with database() as session:
            result = service.get_submission(session, id)
            assert result.status == expected
            assert result.external_receipt is None
            job = session.get(Job, job_id)
            assert job.attempt == job.max_attempts == 1
            assert job.status == "done"
        lines = [json.loads(line) for line in output.getvalue().splitlines()]
        event = next(line for line in lines if line["event"] == f"submission.{expected}")
        assert event["jobId"] == str(job_id)
        assert event["submissionId"] == str(id)
        assert event["requestId"] == correlation
        assert event["attempt"] == 1
        assert event["level"] == "ERROR"
    finally:
        request_id.reset(token)
        logger.removeHandler(handler)


@pytest.mark.parametrize("status,expected", [("applying", "unknown"), ("prepared", "failed")])
def test_restart_recovers_exhausted_apply_without_requeue(database, status, expected):
    id, job_id = seed_apply(database, status)
    with database.begin() as session:
        assert claim(session).id == job_id
        job = session.get(Job, job_id)
        job.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    assert not run_once(database, build_registry())
    with database() as session:
        service.recover_interrupted_submissions(session)
    with database() as session:
        service.recover_interrupted_submissions(session)
    with database() as session:
        assert service.get_submission(session, id).status == expected
        job = session.scalar(select(Job).where(Job.id == job_id))
        assert job.status == "failed"
        assert job.attempt == 1
        assert job.error_code == "LEASE_EXHAUSTED"
    assert not run_once(database, build_registry())


def test_recovery_preserves_active_apply_lease(database):
    id, job_id = seed_apply(database, "applying")
    with database.begin() as session:
        assert claim(session).id == job_id
    with database() as session:
        service.recover_interrupted_submissions(session)
    with database() as session:
        assert service.get_submission(session, id).status == "applying"
