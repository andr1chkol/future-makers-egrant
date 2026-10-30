import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from app.platform.contracts import ConfirmReview, SaveReview
from app.platform.errors import ConflictError, DomainError, NotFoundError, UnavailableError
from app.platform.logging import JsonFormatter, logger, request_id
from app.reviews import service
from app.reviews.models import ReviewRecord, ReviewRevision
from sqlalchemy import func, select


def initialize(factory, context):
    with factory() as session:
        return service.get_review(session, context[0].id)


def save(factory, id, revision, snapshot):
    with factory() as session:
        return service.save_review(session, id, SaveReview(expectedRevision=revision, **snapshot))


def confirm(factory, id, revision):
    with factory() as session:
        return service.confirm_review(session, id, ConfirmReview(expectedRevision=revision))


def test_draft_reload_rows_and_immutable_confirmed_consumer(
    review_database, review_context, corrected_snapshot
):
    extraction, profile, form = review_context
    original = extraction.model_dump_json()
    draft = initialize(review_database, review_context)
    assert draft.revision == 0 and draft.status == "draft"
    assert draft.fields[4].value is None
    corrected_snapshot["fields"][1]["value"] = "Human supplier"
    corrected_snapshot["fields"][2]["value"] = "2026-10-28"
    corrected_snapshot["fields"][5]["value"] = {"amount": "99.90", "currency": "EUR"}
    new_row = corrected_snapshot["tables"][0]["rows"].pop()
    new_row["rowId"] = str(uuid4())
    new_row["cells"][0]["value"] = "Human-added item"
    corrected_snapshot["tables"][0]["rows"].insert(0, new_row)
    saved = save(review_database, extraction.id, 0, corrected_snapshot)
    reloaded = initialize(review_database, review_context)
    assert saved == reloaded
    assert str(saved.tables[0].rows[0].row_id) == new_row["rowId"]
    assert saved.fields[5].value.amount == "99.90"
    with review_database() as session:
        with pytest.raises(ConflictError):
            service.get_confirmed_review(session, extraction.id, 1)
    confirmed = confirm(review_database, extraction.id, 1)
    assert confirmed.revision == 2 and confirmed.confirmed_at.tzinfo
    assert confirm(review_database, extraction.id, 2) == confirmed
    with pytest.raises(ConflictError):
        confirm(review_database, extraction.id, 1)
    with pytest.raises(ConflictError):
        save(review_database, extraction.id, 2, corrected_snapshot)
    with review_database() as session:
        result = service.get_confirmed_review(session, extraction.id, 2)
        assert result.fields[1].value == "Human supplier"
        assert result.tables[0].rows[0].cells[0].value == "Human-added item"
        # The integration's input contains the human values, not the original AI proposal.
        payload_fields = {
            definition.target_tag: next(
                field.value for field in result.fields if field.key == definition.key
            )
            for definition in profile.scalar_fields
        }
        assert payload_fields["supplier"] == "Human supplier"
        assert session.scalar(select(func.count()).select_from(ReviewRevision)) == 3
        assert session.in_transaction()
    assert extraction.model_dump_json() == original


@pytest.mark.parametrize(
    "case",
    [
        "missing_required",
        "bad_money",
        "bad_date",
        "unknown_key",
        "unknown_table",
        "duplicate_key",
        "duplicate_row",
        "unknown_cell",
        "missing_cell",
        "bad_bool",
        "float",
        "invalid_warning",
        "duplicate_warning",
    ],
)
def test_rejects_invalid_snapshots_and_keeps_last_draft(
    review_database, review_context, corrected_snapshot, case
):
    draft = initialize(review_database, review_context)
    if case == "missing_required":
        corrected_snapshot["fields"][0]["value"] = None
    if case == "bad_money":
        corrected_snapshot["fields"][5]["value"] = {"amount": "1,10", "currency": "EUR"}
    if case == "bad_date":
        corrected_snapshot["fields"][2]["value"] = "2026-02-30"
    if case == "unknown_key":
        corrected_snapshot["fields"][0]["key"] = "unknown"
    if case == "unknown_table":
        corrected_snapshot["tables"][0]["key"] = "unknown"
    if case == "duplicate_key":
        corrected_snapshot["fields"].append(corrected_snapshot["fields"][0])
    if case == "duplicate_row":
        corrected_snapshot["tables"][0]["rows"].append(corrected_snapshot["tables"][0]["rows"][0])
    if case == "unknown_cell":
        corrected_snapshot["tables"][0]["rows"][0]["cells"][0]["key"] = "unknown"
    if case == "missing_cell":
        corrected_snapshot["tables"][0]["rows"][0]["cells"].pop()
    if case == "bad_bool":
        corrected_snapshot["fields"][0]["value"] = True
    if case == "float":
        corrected_snapshot["fields"][5]["value"] = 1.1
    if case == "invalid_warning":
        corrected_snapshot["acknowledgedWarnings"] = ["0" * 64]
    if case == "duplicate_warning":
        corrected_snapshot["acknowledgedWarnings"] *= 2
    if case == "missing_required":
        saved = save(review_database, draft.extraction_id, 0, corrected_snapshot)
        with pytest.raises(DomainError) as error:
            confirm(review_database, draft.extraction_id, saved.revision)
        assert error.value.code == "REQUIRED_REVIEW_VALUE"
    else:
        with pytest.raises((DomainError, ValueError)):
            save(review_database, draft.extraction_id, 0, corrected_snapshot)
        assert initialize(review_database, review_context) == draft


def test_warning_required_and_pinned_context_survives_upstream_changes(
    review_database, review_context, corrected_snapshot
):
    draft = initialize(review_database, review_context)
    corrected_snapshot["acknowledgedWarnings"] = []
    save(review_database, draft.extraction_id, 0, corrected_snapshot)
    with pytest.raises(DomainError) as error:
        confirm(review_database, draft.extraction_id, 1)
    assert error.value.code == "UNACKNOWLEDGED_WARNINGS"
    review_context[1].version = 99
    review_context[2].fields.clear()
    assert initialize(review_database, review_context).revision == 1
    with review_database() as session:
        record = session.get(ReviewRecord, draft.extraction_id)
        assert record.profile_snapshot["version"] == 1
        assert record.form_snapshot["fields"]


def test_option_keys_and_empty_table_deletion(review_database, review_context, corrected_snapshot):
    from app.platform.contracts import Option

    review_context[2].fields[1].options = [Option(key="supplier-1", label="Display supplier")]
    review_context[0].fields[1].value = "supplier-1"
    draft = initialize(review_database, review_context)
    corrected_snapshot["fields"][1]["value"] = "Display supplier"
    with pytest.raises(DomainError) as error:
        save(review_database, draft.extraction_id, 0, corrected_snapshot)
    assert error.value.code == "INVALID_REVIEW_OPTION"
    corrected_snapshot["fields"][1]["value"] = "supplier-1"
    corrected_snapshot["tables"][0]["rows"] = []
    saved = save(review_database, draft.extraction_id, 0, corrected_snapshot)
    assert not saved.tables[0].rows
    assert confirm(review_database, draft.extraction_id, 1).status == "confirmed"


def test_parallel_initialize_and_confirm_are_serialized(
    review_database, review_context, corrected_snapshot
):
    barrier = Barrier(2)

    def first_read():
        barrier.wait()
        return initialize(review_database, review_context)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: first_read(), range(2)))
    assert results[0] == results[1]
    save(review_database, results[0].extraction_id, 0, corrected_snapshot)
    barrier = Barrier(2)

    def attempt():
        barrier.wait()
        try:
            return confirm(review_database, results[0].extraction_id, 1).status
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: attempt(), range(2))) == ["confirmed", "conflict"]
    assert confirm(review_database, results[0].extraction_id, 2).status == "confirmed"


def test_stale_put_and_logs_do_not_expose_values(
    review_database, review_context, corrected_snapshot
):
    draft = initialize(review_database, review_context)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    capture = Capture()
    logger.addHandler(handler)
    logger.addHandler(capture)
    correlation = str(uuid4())
    token = request_id.set(correlation)
    corrected_snapshot["fields"][1]["value"] = "PRIVATE-PERSON sk-private-key IBAN SK12345"
    try:
        save(review_database, draft.extraction_id, 0, corrected_snapshot)
        with pytest.raises(ConflictError):
            save(review_database, draft.extraction_id, 0, corrected_snapshot)
        confirm(review_database, draft.extraction_id, 1)
    finally:
        request_id.reset(token)
        logger.removeHandler(handler)
        logger.removeHandler(capture)
    logs = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert [item["event"] for item in logs] == [
        "review.saved",
        "review.conflict",
        "review.confirmed",
    ]
    assert [item["level"] for item in logs] == ["INFO", "WARNING", "INFO"]
    assert all(
        item["requestId"] == correlation and item["extractionId"] == str(draft.extraction_id)
        for item in logs
    )
    assert logs[1]["errorCode"] == "STALE_REVIEW"
    assert [record.context["revision"] for record in records] == [1, 1, 2]
    assert "PRIVATE" not in stream.getvalue() and "SK12345" not in stream.getvalue()


def test_missing_and_not_ready_and_no_fixture_fallback(
    review_database, review_context, monkeypatch
):
    review_context[0].status = "running"
    with pytest.raises(ConflictError):
        initialize(review_database, review_context)
    with review_database() as session:
        with pytest.raises(NotFoundError):
            service.get_confirmed_review(session, uuid4(), 0)
    from app.reviews.context import load_context

    with review_database() as session:
        with pytest.raises(UnavailableError):
            load_context(session, uuid4())


def test_empty_tables_still_validate_pinned_column_mappings(review_database, review_context):
    review_context[0].tables[0].rows.clear()
    review_context[1].table_fields[0].columns[0].target_tag = "unknown_column"
    with pytest.raises(DomainError) as error:
        initialize(review_database, review_context)
    assert error.value.code == "PROFILE_MISMATCH"


def test_parallel_draft_writes_have_exactly_one_winner(
    review_database, review_context, corrected_snapshot
):
    draft = initialize(review_database, review_context)
    barrier = Barrier(2)

    def attempt(value):
        snapshot = json.loads(json.dumps(corrected_snapshot))
        snapshot["fields"][1]["value"] = value
        barrier.wait()
        try:
            save(review_database, draft.extraction_id, 0, snapshot)
            return value
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["First correction", "Second correction"]))
    assert results.count("conflict") == 1
    winner = next(result for result in results if result != "conflict")
    reloaded = initialize(review_database, review_context)
    assert reloaded.revision == 1 and reloaded.fields[1].value == winner


def test_required_whitespace_and_warning_duplicates(
    review_database, review_context, corrected_snapshot
):
    review_context[0].warnings *= 2
    draft = initialize(review_database, review_context)
    corrected_snapshot["fields"][0]["value"] = "   "
    save(review_database, draft.extraction_id, 0, corrected_snapshot)
    with pytest.raises(DomainError) as error:
        confirm(review_database, draft.extraction_id, 1)
    assert error.value.code == "REQUIRED_REVIEW_VALUE"
    corrected_snapshot["fields"][0]["value"] = "Human invoice"
    save(review_database, draft.extraction_id, 1, corrected_snapshot)
    assert confirm(review_database, draft.extraction_id, 2).status == "confirmed"


def test_confirmed_wire_result_stays_identical_in_non_utc_database_session(
    review_database, review_context, corrected_snapshot
):
    from datetime import timedelta

    from sqlalchemy.orm import Session

    with review_database.kw["bind"].connect() as connection:
        connection.exec_driver_sql("SET TIME ZONE 'Europe/Bratislava'")
        connection.commit()
        try:
            with Session(bind=connection, expire_on_commit=False) as session:
                service.get_review(session, review_context[0].id)
                service.save_review(
                    session,
                    review_context[0].id,
                    SaveReview(expectedRevision=0, **corrected_snapshot),
                )
                first = service.confirm_review(
                    session, review_context[0].id, ConfirmReview(expectedRevision=1)
                )
            with Session(bind=connection, expire_on_commit=False) as session:
                repeated = service.confirm_review(
                    session, review_context[0].id, ConfirmReview(expectedRevision=2)
                )
                assert repeated.confirmed_at.utcoffset() == timedelta(0)
                assert repeated.model_dump(mode="json") == first.model_dump(mode="json")
            with Session(bind=connection) as session:
                reloaded = service.get_review(session, review_context[0].id)
                consumed = service.get_confirmed_review(session, review_context[0].id, 2)
                assert reloaded.model_dump(mode="json") == first.model_dump(mode="json")
                assert consumed.model_dump(mode="json") == first.model_dump(mode="json")
        finally:
            connection.exec_driver_sql("RESET TIME ZONE")
            connection.commit()
