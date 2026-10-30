import json
import threading
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
import yaml
from app.extraction.models import ExtractionRecord
from app.extraction.providers import ProviderError
from app.extraction.routes import router
from app.extraction.service import (
    MAX_ATTEMPTS,
    ExtractionRetryScheduled,
    create_extractions,
    get_extraction,
    process_extraction,
    retry_extraction,
)
from app.main import ERROR_RESPONSES, create_app
from app.platform.access import require_access
from app.platform.contracts import CreateExtractions, NormalizedDocument
from app.platform.errors import ConflictError, DomainError, NotFoundError, ValidationError
from app.platform.jobs import JobRegistry, run_once
from app.platform.models import Job
from extraction_support import (
    ROOT,
    ScriptedProvider,
    example_document,
    example_profile,
    money,
    reply_for,
    value,
)
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

PROFILE = example_profile()
DOCUMENT = example_document()


def good_reply(total="55.00"):
    return reply_for(
        PROFILE,
        {
            "supplier": value("Demo Paper s.r.o.", "row-2"),
            "buyer": value("Demo Grant Association", "row-2"),
            "total": money(total, "EUR", "row-4", "55.00"),
        },
        {
            "items": [
                {"description": value("Workshop notebooks", "row-2")},
                {"description": value("Training materials", "row-3")},
            ]
        },
    )


def create(database, *document_ids):
    request = CreateExtractions(
        document_ids=list(document_ids) or [DOCUMENT.document_id],
        profile_id=PROFILE.id,
        profile_version=1,
    )
    with database() as session:
        return create_extractions(session, request).extractions


def read(database, id):
    with database() as session:
        return get_extraction(session, id)


def process(database, id, provider):
    with database() as session:
        process_extraction(session, id, provider=provider)


def make_ready_for_next_attempt(database):
    with database.begin() as session:
        session.execute(
            update(Job).values(
                available_at=session.scalar(select(func.now())) - timedelta(seconds=1)
            )
        )


def worker(provider) -> JobRegistry:
    registry = JobRegistry()
    registry.register_handler(
        "extraction.process",
        lambda session, id: process_extraction(session, id, provider=provider),
    )
    return registry


def test_batch_creates_one_queued_extraction_and_job_per_document(database, modules):
    second = NormalizedDocument.model_validate(
        {**DOCUMENT.model_dump(mode="json", by_alias=True), "documentId": str(uuid4())}
    )
    modules.add_document(second)
    queued = create(database, DOCUMENT.document_id, second.document_id)
    assert [item.document_id for item in queued] == [DOCUMENT.document_id, second.document_id]
    assert {item.status for item in queued} == {"queued"}
    with database() as session:
        jobs = session.scalars(select(Job)).all()
        assert sorted(job.payload["resource_id"] for job in jobs) == sorted(
            str(item.id) for item in queued
        )
        assert {job.kind for job in jobs} == {"extraction.process"}
        record = session.get(ExtractionRecord, queued[0].id)
        assert record.profile_snapshot == PROFILE.model_dump(mode="json", by_alias=True)
        assert record.mode == "fixture"


def test_creation_validates_inputs_before_queueing(database, modules):
    with pytest.raises(ValidationError):
        create(database, DOCUMENT.document_id, DOCUMENT.document_id)
    with pytest.raises(NotFoundError):
        create(database, uuid4())
    modules.not_ready.add(DOCUMENT.document_id)
    with pytest.raises(ConflictError):
        create(database)
    with pytest.raises(NotFoundError):
        with database() as session:
            create_extractions(
                session,
                CreateExtractions(
                    document_ids=[DOCUMENT.document_id], profile_id=PROFILE.id, profile_version=7
                ),
            )
    with database() as session:
        assert session.scalar(select(func.count()).select_from(ExtractionRecord)) == 0
        assert session.scalar(select(func.count()).select_from(Job)) == 0


def test_live_mode_without_provider_settings_is_unavailable(database, modules, monkeypatch):
    from app.platform.settings import get_settings

    monkeypatch.setattr(get_settings(), "app_mode", "live")
    monkeypatch.setattr(get_settings(), "openai_api_key", None)
    with pytest.raises(DomainError) as raised:
        create(database)
    assert (raised.value.code, raised.value.status) == ("AI_NOT_CONFIGURED", 503)


def test_worker_produces_a_persisted_ready_extraction(database, modules, captured_logs):
    (queued,) = create(database)
    provider = ScriptedProvider(good_reply())
    assert run_once(database, worker(provider))
    first = read(database, queued.id)
    assert first.status == "ready" and first.error is None and first.mode == "fixture"
    assert {field.key: field.status for field in first.fields}["total"] == "found"
    # Row IDs are stored, not regenerated on read.
    second = read(database, queued.id)
    assert [row.row_id for row in second.tables[0].rows] == [
        row.row_id for row in first.tables[0].rows
    ]
    events = [record["event"] for record in captured_logs()]
    assert events.index("extraction.started") < events.index("extraction.ready")
    ready = next(r for r in captured_logs() if r["event"] == "extraction.ready")
    assert ready["extractionId"] == str(queued.id)
    assert ready["documentId"] == str(DOCUMENT.document_id)
    assert ready["attempt"] == 1 and isinstance(ready["durationMs"], int)
    warnings = [r for r in captured_logs() if r["event"] == "extraction.validation_warning"]
    assert {r["errorCode"] for r in warnings} >= {"REQUIRED_VALUE_MISSING"}
    assert {r["level"] for r in warnings} == {"WARNING"}


def test_fixture_mode_uses_the_recorded_reply_for_the_shared_example(database, modules):
    (queued,) = create(database)
    process(database, queued.id, provider=None)
    result = read(database, queued.id)
    assert result.status == "ready"
    assert [w.code for w in result.warnings] == ["MISSING_OPTIONAL_VALUE"]


def test_transient_failures_are_retried_and_bounded(database, modules, captured_logs):
    (queued,) = create(database)
    provider = ScriptedProvider(ProviderError("AI_RATE_LIMITED", retryable=True))
    registry = worker(provider)
    for _ in range(2):
        assert run_once(database, registry)
        assert read(database, queued.id).status == "queued"
        make_ready_for_next_attempt(database)
    assert run_once(database, registry)
    failed = read(database, queued.id)
    assert failed.status == "failed"
    assert failed.error.code == "AI_RATE_LIMITED"
    assert provider.calls == 3
    with database() as session:
        job = session.scalars(select(Job)).one()
        assert (job.status, job.attempt) == ("done", 3)
    assert not run_once(database, registry)
    retries = [r for r in captured_logs() if r["event"] == "job.retry_scheduled"]
    assert any(r.get("extractionId") == str(queued.id) for r in retries)
    assert {r["errorCode"] for r in retries if "extractionId" in r} == {"AI_RATE_LIMITED"}
    failure = next(r for r in captured_logs() if r["event"] == "extraction.failed")
    assert failure["level"] == "ERROR" and failure["attempt"] == 3


def test_transient_failure_then_success(database, modules):
    (queued,) = create(database)
    provider = ScriptedProvider(ProviderError("AI_TIMEOUT", retryable=True), good_reply())
    registry = worker(provider)
    assert run_once(database, registry)
    make_ready_for_next_attempt(database)
    assert run_once(database, registry)
    assert read(database, queued.id).status == "ready"


@pytest.mark.parametrize(
    ("outcome", "code"),
    [
        (ProviderError("AI_AUTH_FAILED", retryable=False), "AI_AUTH_FAILED"),
        (ProviderError("FIXTURE_NOT_AVAILABLE", retryable=False), "FIXTURE_NOT_AVAILABLE"),
    ],
)
def test_permanent_failures_fail_without_retry(database, modules, outcome, code):
    (queued,) = create(database)
    provider = ScriptedProvider(outcome)
    assert run_once(database, worker(provider))
    failed = read(database, queued.id)
    assert (failed.status, failed.error.code, provider.calls) == ("failed", code, 1)
    assert failed.fields == [] and failed.tables == []


def test_malformed_output_is_retried_then_fails(database, modules):
    (queued,) = create(database)
    provider = ScriptedProvider("{not json")
    for _ in range(3):
        with database() as session:
            try:
                process_extraction(session, queued.id, provider=provider)
            except ExtractionRetryScheduled:
                pass
    failed = read(database, queued.id)
    assert (failed.status, failed.error.code) == ("failed", "AI_OUTPUT_INVALID")


def test_unexpected_errors_never_leave_the_run_running(database, modules, captured_logs):
    (queued,) = create(database)
    provider = ScriptedProvider(RuntimeError("document text: IBAN SK3112000000198742637541"))
    for _ in range(3):
        with database() as session:
            try:
                process_extraction(session, queued.id, provider=provider)
            except ExtractionRetryScheduled:
                pass
    failed = read(database, queued.id)
    assert (failed.status, failed.error.code) == ("failed", "EXTRACTION_INTERNAL_ERROR")
    assert "SK3112000000198742637541" not in captured_logs.text()
    final = next(r for r in captured_logs() if r["event"] == "extraction.failed")
    assert final["stack"]


def test_provider_mode_must_match_the_run(database, modules):
    (queued,) = create(database)
    process(database, queued.id, ScriptedProvider(good_reply(), mode="live"))
    failed = read(database, queued.id)
    assert (failed.status, failed.error.code) == ("failed", "AI_NOT_CONFIGURED")


def test_unavailable_document_fails_the_run(database, modules):
    (queued,) = create(database)
    modules.documents.clear()
    provider = ScriptedProvider(good_reply())
    process(database, queued.id, provider)
    failed = read(database, queued.id)
    assert (failed.status, failed.error.code, provider.calls) == (
        "failed",
        "DOCUMENT_UNAVAILABLE",
        0,
    )


def test_duplicate_job_execution_does_not_change_a_finished_result(database, modules):
    (queued,) = create(database)
    process(database, queued.id, ScriptedProvider(good_reply()))
    first = read(database, queued.id)
    late = ScriptedProvider(good_reply(total="1.00"))
    process(database, queued.id, late)
    assert late.calls == 0
    assert read(database, queued.id) == first


def test_late_worker_cannot_overwrite_a_newer_run(database, modules):
    """A worker whose lease expired mid-call must discard its result."""
    (queued,) = create(database)
    newer = ScriptedProvider(good_reply(total="55.00"))

    def reclaimed_during_call():
        # Another worker claims and finishes the same extraction while this call waits.
        process(database, queued.id, newer)
        return good_reply(total="99.00")

    process(database, queued.id, ScriptedProvider(reclaimed_during_call))
    result = read(database, queued.id)
    total = {field.key: field for field in result.fields}["total"]
    assert total.model_dump(mode="json")["value"]["amount"] == "55.00"
    with database() as session:
        assert session.get(ExtractionRecord, queued.id).attempt == 2


def test_concurrent_claims_produce_exactly_one_result(database, modules):
    (queued,) = create(database)
    barrier = threading.Barrier(2)
    errors = []

    def run(total):
        def reply():
            barrier.wait(timeout=10)
            return good_reply(total=total)

        try:
            process(database, queued.id, ScriptedProvider(reply))
        except Exception as error:  # pragma: no cover - surfaced below
            errors.append(error)

    threads = [threading.Thread(target=run, args=(total,)) for total in ("55.00", "77.00")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    assert errors == []
    result = read(database, queued.id)
    assert result.status == "ready"
    with database() as session:
        record = session.get(ExtractionRecord, queued.id)
        assert record.attempt == 2 and record.run_token is None


def test_retry_keeps_the_id_and_only_applies_to_failed_runs(database, modules):
    (queued,) = create(database)
    process(database, queued.id, ScriptedProvider(ProviderError("AI_AUTH_FAILED", False)))
    with database() as session:
        retried = retry_extraction(session, queued.id)
    assert (retried.id, retried.status, retried.error) == (queued.id, "queued", None)
    with database() as session:
        assert session.scalar(select(func.count()).select_from(Job)) == 2
    assert run_once(database, worker(ScriptedProvider(good_reply())))
    make_ready_for_next_attempt(database)
    assert run_once(database, worker(ScriptedProvider(good_reply())))
    ready = read(database, queued.id)
    assert ready.status == "ready"
    with database() as session, pytest.raises(ConflictError):
        retry_extraction(session, queued.id)
    with database() as session, pytest.raises(NotFoundError):
        retry_extraction(session, uuid4())


def age_run(database, id, status, minutes=6):
    """Leave a run as a dead worker would: untouched in a non-final state."""
    with database.begin() as session:
        now = session.scalar(select(func.now()))
        session.execute(
            update(ExtractionRecord)
            .where(ExtractionRecord.id == id)
            .values(
                status=status,
                run_token=uuid4() if status == "running" else None,
                attempt=MAX_ATTEMPTS,
                updated_at=now - timedelta(minutes=minutes),
            )
        )
        # The platform has given up on the job, so nothing will pick the run up again.
        session.execute(update(Job).values(status="failed", error_code="LEASE_EXHAUSTED"))


@pytest.mark.parametrize("status", ["running", "queued"])
def test_stale_runs_without_a_job_can_be_retried(database, modules, status):
    (queued,) = create(database)
    age_run(database, queued.id, status)
    with database() as session:
        retried = retry_extraction(session, queued.id)
    assert (retried.id, retried.status, retried.error) == (queued.id, "queued", None)
    with database() as session:
        record = session.get(ExtractionRecord, queued.id)
        assert (record.attempt, record.run_token) == (0, None)
    assert run_once(database, worker(ScriptedProvider(good_reply())))
    assert read(database, queued.id).status == "ready"


@pytest.mark.parametrize("status", ["running", "queued"])
def test_recent_unfinished_runs_cannot_be_retried(database, modules, status):
    (queued,) = create(database)
    age_run(database, queued.id, status, minutes=1)
    with database() as session, pytest.raises(ConflictError):
        retry_extraction(session, queued.id)


def test_old_worker_cannot_overwrite_a_retried_stale_run(database, modules):
    (queued,) = create(database)
    old_worker_claimed = threading.Event()
    release_old_worker = threading.Event()

    class SlowProvider(ScriptedProvider):
        def extract(self, profile, options, document):
            old_worker_claimed.set()
            release_old_worker.wait(timeout=10)
            return json.dumps(good_reply(total="99.00"))

    old = threading.Thread(target=process, args=(database, queued.id, SlowProvider()))
    old.start()
    assert old_worker_claimed.wait(timeout=10)
    with database.begin() as session:
        session.execute(
            update(ExtractionRecord)
            .where(ExtractionRecord.id == queued.id)
            .values(updated_at=func.now() - timedelta(minutes=6))
        )
    with database() as session:
        retry_extraction(session, queued.id)
    process(database, queued.id, ScriptedProvider(good_reply()))
    release_old_worker.set()
    old.join(timeout=10)
    ready = read(database, queued.id)
    assert ready.status == "ready"
    total = next(field for field in ready.fields if field.key == "total")
    assert total.value.amount == "55.00"


def assembled_app():
    """Mount this router the way member 5 will: in front of the shells, behind the gate."""
    app = create_app()
    app.include_router(router, prefix="/api/v1", dependencies=[Depends(require_access)])
    # Routes match in order; the extraction router must win over the 503 shells.
    app.router.routes.insert(0, app.router.routes.pop())
    return app


def test_http_routes(database, modules):
    with TestClient(assembled_app(), base_url="http://localhost") as client:
        origin = {"Origin": "http://localhost:5173"}
        body = {
            "documentIds": [str(DOCUMENT.document_id)],
            "profileId": str(PROFILE.id),
            "profileVersion": 1,
        }
        created = client.post("/api/v1/extractions", json=body, headers=origin)
        assert created.status_code == 202, created.text
        (item,) = created.json()["data"]["extractions"]
        assert item["status"] == "queued"
        detail = client.get(f"/api/v1/extractions/{item['id']}")
        assert detail.status_code == 200
        assert detail.json()["data"]["documentId"] == str(DOCUMENT.document_id)
        assert detail.json()["data"]["fields"] == []
        listed = client.get("/api/v1/extractions?limit=1&offset=0").json()
        assert listed["pagination"] == {"limit": 1, "offset": 0, "total": 1}
        assert (
            client.post(f"/api/v1/extractions/{item['id']}/retries", headers=origin).json()[
                "error"
            ]["code"]
            == "CONFLICT"
        )
        assert client.get(f"/api/v1/extractions/{uuid4()}").status_code == 404
        assert (
            client.post(
                "/api/v1/extractions", json={**body, "profileVersion": 0}, headers=origin
            ).status_code
            == 422
        )
        modules.not_ready.add(DOCUMENT.document_id)
        assert client.post("/api/v1/extractions", json=body, headers=origin).status_code == 409


def test_routes_require_the_access_gate(database, modules):
    with TestClient(assembled_app(), base_url="http://external.example") as client:
        assert client.get("/api/v1/extractions").status_code == 401


def test_routes_match_the_frozen_contract():
    frozen = yaml.safe_load((ROOT / "contracts/api.yaml").read_text())
    app = FastAPI(responses=ERROR_RESPONSES)
    app.include_router(router, prefix="/api/v1")
    assembled = app.openapi()
    for path in (
        "/api/v1/extractions",
        "/api/v1/extractions/{id}",
        "/api/v1/extractions/{id}/retries",
    ):
        for method, operation in frozen["paths"][path].items():
            ours = assembled["paths"][path][method]
            assert ours["responses"].keys() == operation["responses"].keys(), (path, method)
            for status, response in operation["responses"].items():
                assert ours["responses"][status].get("content") == response.get("content")
            assert ours.get("requestBody") == operation.get("requestBody")
            assert ours.get("parameters") == operation.get("parameters")


def test_stored_rows_and_timestamps_use_contract_formats(database, modules):
    (queued,) = create(database)
    process(database, queued.id, ScriptedProvider(good_reply()))
    with database() as session:
        record = session.get(ExtractionRecord, queued.id)
        assert all(UUID(row["rowId"]) for row in record.tables[0]["rows"])
    assert read(database, queued.id).created_at.utcoffset() == timedelta(0)


def test_logs_never_contain_document_values(database, modules, captured_logs):
    (queued,) = create(database)
    process(database, queued.id, ScriptedProvider(good_reply()))
    text = captured_logs.text()
    for private in ("Demo Paper", "Demo Grant", "55.00", "Workshop", "row-2"):
        assert private not in text
