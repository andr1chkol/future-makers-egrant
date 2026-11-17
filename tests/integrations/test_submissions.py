import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from app.integrations import dependencies, service
from app.integrations.models import SubmissionRecord
from app.integrations.payload import build_submission_payload
from app.main import create_app
from app.platform import contracts as c
from app.platform.errors import ConflictError, UnavailableError, ValidationError
from app.platform.logging import JsonFormatter, logger
from app.platform.models import Job
from fastapi.testclient import TestClient
from sqlalchemy import func, select

EXAMPLES = Path(__file__).resolve().parents[2] / "contracts/examples"


def example(name, model):
    return model.model_validate_json((EXAMPLES / f"{name}.json").read_text())


@pytest.fixture
def context(monkeypatch):
    values = {
        "review": example("review", c.Review),
        "extraction": example("extraction", c.Extraction),
        "profile": example("profile", c.Profile),
        "form": example("form", c.FormDefinition),
    }
    monkeypatch.setattr(dependencies, "get_confirmed_review", lambda *args: values["review"])
    monkeypatch.setattr(dependencies, "get_extraction", lambda *args: values["extraction"])
    monkeypatch.setattr(dependencies, "get_profile", lambda *args: values["profile"])
    monkeypatch.setattr(dependencies, "get_form", lambda *args: values["form"])
    return values


def request_for(context, **changes):
    return c.CreateSubmission(
        review_id=context["review"].extraction_id,
        review_revision=context["review"].revision,
        mode="export",
        target_context=c.TargetContext(application_id=None),
        acknowledge_overwrite=False,
    ).model_copy(update=changes)


def test_exact_corrected_export_survives_reload_and_dependency_loss(database, context, monkeypatch):
    with database() as session:
        created = service.create_submission(session, request_for(context), "stable-intent")
    expected = example("submission", c.Submission).payload
    assert created.payload == expected
    for name in ["get_confirmed_review", "get_extraction", "get_profile", "get_form"]:
        monkeypatch.setattr(
            dependencies, name, lambda *args: pytest.fail("Must use persisted payload")
        )
    with database() as session:
        assert service.export_submission(session, created.id) == expected
    with database() as session:
        assert service.export_submission(session, created.id) == expected
    with database() as session:
        reloaded = service.get_submission(session, created.id)
        assert reloaded.status == "exported"
        assert reloaded.external_receipt is None
    with database() as session:
        assert service.create_submission(session, request_for(context), "stable-intent") == reloaded
    with database() as session:
        assert session.scalar(select(func.count()).select_from(Job)) == 0


@pytest.mark.parametrize(
    "change", ["mode", "review_revision", "target_context", "acknowledge_overwrite"]
)
def test_key_rejects_changed_intent(database, context, change):
    original = request_for(context)
    with database() as session:
        service.create_submission(session, original, "same-key")
    values = {
        "mode": "egrant",
        "review_revision": 3,
        "target_context": c.TargetContext(application_id="different-target"),
        "acknowledge_overwrite": True,
    }
    with database() as session, pytest.raises(ConflictError):
        service.create_submission(
            session, original.model_copy(update={change: values[change]}), "same-key"
        )


def test_concurrent_same_key_creates_one_operation(database, context, monkeypatch):
    barrier = Barrier(2)
    original = dependencies.get_confirmed_review

    def concurrent_read(*args):
        barrier.wait(timeout=10)
        return original(*args)

    monkeypatch.setattr(dependencies, "get_confirmed_review", concurrent_read)

    def create(_):
        with database() as session:
            return service.create_submission(session, request_for(context), "concurrent-key").id

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(create, range(2)))
    assert ids[0] == ids[1]
    with database() as session:
        assert session.scalar(select(func.count()).select_from(SubmissionRecord)) == 1


@pytest.mark.parametrize(
    "mutation", ["draft", "stale", "unconfirmed", "wrong_extraction", "wrong_profile", "warnings"]
)
def test_unconfirmed_and_stale_reviews_leave_no_operation(database, context, mutation):
    if mutation == "draft":
        context["review"].status = "draft"
    elif mutation == "stale":
        context["review"].revision += 1
    elif mutation == "unconfirmed":
        context["review"].confirmed_at = None
    elif mutation == "wrong_extraction":
        context["extraction"].id = uuid4()
    elif mutation == "wrong_profile":
        context["profile"].version += 1
    else:
        context["review"].acknowledged_warnings = []
    request = request_for(context)
    if mutation == "stale":
        request.review_revision -= 1
    with database() as session, pytest.raises(ConflictError):
        service.create_submission(session, request, "invalid-review")
    with database() as session:
        assert session.scalar(select(func.count()).select_from(SubmissionRecord)) == 0


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_key",
        "duplicate_field",
        "unknown_target",
        "duplicate_target",
        "missing_required",
        "wrong_type",
        "wrong_option",
        "missing_column",
        "duplicate_row",
        "duplicate_table",
        "unknown_column",
        "empty_table_mapping",
        "missing_target_required",
    ],
)
def test_invalid_mapping_and_values_are_rejected(context, mutation):
    review, profile, form = context["review"], context["profile"], context["form"]
    if mutation == "unknown_key":
        review.fields[0].key = "injected"
    elif mutation == "duplicate_field":
        review.fields.append(review.fields[0])
    elif mutation == "unknown_target":
        profile.scalar_fields[0].target_tag = "injected"
    elif mutation == "duplicate_target":
        profile.scalar_fields[0].target_tag = profile.scalar_fields[1].target_tag
    elif mutation == "missing_required":
        review.fields[0].value = None
    elif mutation == "wrong_type":
        review.tables[0].rows[0].cells[1].value = "not-a-decimal"
    elif mutation == "wrong_option":
        form.fields[0].options = [c.Option(key="allowed", label="Allowed")]
    elif mutation == "missing_column":
        review.tables[0].rows[0].cells.pop()
    elif mutation == "duplicate_row":
        review.tables[0].rows.append(review.tables[0].rows[0])
    elif mutation == "duplicate_table":
        review.tables.append(review.tables[0])
    elif mutation == "unknown_column":
        profile.table_fields[0].columns[0].target_tag = "injected"
    elif mutation == "empty_table_mapping":
        review.tables[0].rows = []
        profile.table_fields[0].columns[0].target_tag = "injected"
    else:
        form.fields.append(
            c.FormField(
                tag="required-unmapped",
                label="Required",
                type="string",
                required=True,
                options=None,
            )
        )
    with pytest.raises(ValidationError):
        build_submission_payload(review, context["extraction"], profile, form)


def test_another_profile_maps_tags_and_preserves_null_false_decimal_and_human_rows(context):
    review, profile, form = context["review"], context["profile"], context["form"]
    profile.scalar_fields = [
        c.ProfileField(
            key="enabled",
            label="Enabled",
            type="boolean",
            description="",
            required=True,
            target_tag="active",
        ),
        c.ProfileField(
            key="note",
            label="Note",
            type="string",
            description="",
            required=False,
            target_tag="memo",
        ),
    ]
    form.fields = [
        c.FormField(tag="active", label="Active", type="boolean", required=True, options=None),
        c.FormField(tag="memo", label="Memo", type="string", required=False, options=None),
    ]
    review.fields = [
        c.ReviewField(key="enabled", value=False),
        c.ReviewField(key="note", value=None),
    ]
    profile.table_fields[0].target_tag = "budget"
    profile.table_fields[0].write_mode = "replace"
    form.tables[0].tag = "budget"
    review.tables[0].rows[0].row_id = uuid4()
    review.tables[0].rows[0].cells[1].value = "0.00"
    payload = build_submission_payload(review, context["extraction"], profile, form)
    assert [(f.target_tag, f.value) for f in payload.fields] == [("active", False), ("memo", None)]
    assert payload.tables[0].target_tag == "budget"
    assert payload.tables[0].write_mode == "replace"
    assert payload.tables[0].rows[0].values["quantity"] == "0.00"
    assert payload.tables[0].rows[0].row_id == review.tables[0].rows[0].row_id


def test_unavailable_owner_and_egrant_fail_honestly(database, monkeypatch):
    def owner_unavailable(*args):
        raise UnavailableError()

    monkeypatch.setattr(dependencies, "get_confirmed_review", owner_unavailable)
    request = c.CreateSubmission(
        review_id=uuid4(),
        review_revision=1,
        mode="export",
        target_context=c.TargetContext(application_id=None),
        acknowledge_overwrite=False,
    )
    with database() as session, pytest.raises(UnavailableError):
        service.create_submission(session, request, "missing-owner")
    request.mode = "egrant"
    request.acknowledge_overwrite = True
    with database() as session, pytest.raises(UnavailableError):
        service.create_submission(session, request, "missing-interface")
    with database() as session:
        assert session.scalar(select(func.count()).select_from(SubmissionRecord)) == 0
        assert session.scalar(select(func.count()).select_from(Job)) == 0


def test_http_attachment_schema_access_and_safe_request_logs(database, context, monkeypatch):
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    try:
        with TestClient(create_app(), base_url="http://localhost") as client:
            response = client.post(
                "/api/v1/submissions",
                json=request_for(context).model_dump(mode="json", by_alias=True),
                headers={
                    "Origin": "http://localhost:5173",
                    "Idempotency-Key": "private-key-marker",
                },
            )
            assert response.status_code == 201
            c.Submission.model_validate(response.json()["data"])
            id = response.json()["data"]["id"]
            attachment = client.get(f"/api/v1/submissions/{id}/export")
            assert attachment.status_code == 200
            assert (
                attachment.headers["Content-Disposition"]
                == f'attachment; filename="submission-{id}.json"'
            )
            assert attachment.json() == response.json()["data"]["payload"]
            assert attachment.headers["cache-control"] == "no-store"
            assert client.get(f"/api/v1/submissions/{uuid4()}").status_code == 404
            assert (
                client.post(
                    "/api/v1/submissions",
                    json={"payload": "secret"},
                    headers={"Origin": "http://localhost:5173"},
                ).status_code
                == 422
            )
            monkeypatch.setenv("DEV_AUTH_BYPASS", "false")
            monkeypatch.setenv("ACCESS_CODE", "test-access-code-long-enough")
            from app.platform.settings import get_settings

            get_settings.cache_clear()
            assert client.get(f"/api/v1/submissions/{id}").status_code == 401
            assert client.get(f"/api/v1/submissions/{id}/export").status_code == 401
        logs = [json.loads(line) for line in output.getvalue().splitlines()]
        prepared = next(log for log in logs if log["event"] == "submission.prepared")
        assert prepared["submissionId"] == id
        assert prepared["requestId"] == response.headers["x-request-id"]
        assert prepared["level"] == "INFO"
        assert prepared["durationMs"] >= 0
        assert "private-key-marker" not in output.getvalue()
        assert "HUMAN-PO-001" not in output.getvalue()
        assert "Demo Paper" not in output.getvalue()
    finally:
        logger.removeHandler(handler)


def test_payload_serialization_failure_rolls_back_operation(database, context, monkeypatch):
    def fail_serialization(record):
        raise RuntimeError("test-only failure after insert")

    monkeypatch.setattr(service, "submission_dto", fail_serialization)
    with database() as session, pytest.raises(RuntimeError):
        service.create_submission(session, request_for(context), "rollback-key")
    with database() as session:
        assert session.scalar(select(func.count()).select_from(SubmissionRecord)) == 0


def test_concurrent_changed_intent_conflicts_without_overwriting_winner(
    database, context, monkeypatch
):
    barrier = Barrier(2)
    original = dependencies.get_confirmed_review

    def concurrent_read(*args):
        barrier.wait(timeout=10)
        return original(*args)

    monkeypatch.setattr(dependencies, "get_confirmed_review", concurrent_read)

    def create(target):
        request = request_for(context, target_context=c.TargetContext(application_id=target))
        with database() as session:
            try:
                return service.create_submission(session, request, "racing-intent")
            except ConflictError:
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, ["first", "second"]))
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    with database() as session:
        assert session.scalar(select(func.count()).select_from(SubmissionRecord)) == 1
        assert service.get_submission(session, winners[0].id) == winners[0]
