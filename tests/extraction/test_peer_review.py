import json
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from app.extraction.assembly import assemble_extraction
from app.extraction.models import ExtractionRecord
from app.extraction.schema import parse_provider_output
from app.extraction.service import (
    create_extractions,
    get_extraction,
    recover_terminal_extractions,
    to_dto,
)
from app.platform.contracts import CreateExtractions, NormalizedDocument
from app.platform.models import Job
from extraction_support import example_document, example_profile, money, reply_for, value
from sqlalchemy import func, update


def assembled(text, field):
    profile = example_profile()
    document = NormalizedDocument.model_validate(
        {
            "documentId": str(uuid4()),
            "units": [{"id": "u", "text": text, "page": 1, "sheet": None, "cell": None}],
        }
    )
    raw = parse_provider_output(json.dumps(reply_for(profile, field)), profile)
    return assemble_extraction(raw, profile, document, {})


def test_whitespace_matching_returns_an_exact_source_excerpt():
    source = "Supplier: Demo   Paper\ns.r.o."
    result = assembled(source, {"supplier": value("Demo Paper s.r.o.", "u")})
    supplier = next(field for field in result.fields if field.key == "supplier")
    assert supplier.status == "found"
    assert supplier.sources[0].quote == "Demo   Paper\ns.r.o."
    assert supplier.sources[0].quote in source


@pytest.mark.parametrize(
    "source",
    [
        "-12,50 EUR",
        "12,50- EUR",
        "(12,50) EUR",
        "−12,50 EUR",
        "- 12,50 EUR",
        "12,50 - EUR",
        "( 12,50 ) EUR",
    ],
)
@pytest.mark.parametrize("quote", ["12,50", None])
def test_positive_amount_cannot_be_found_inside_a_printed_debit(source, quote):
    proposed = money("12,50", "EUR", "u")
    proposed["evidence"][0]["quote"] = quote
    result = assembled(source, {"total": proposed})
    total = next(field for field in result.fields if field.key == "total")
    assert total.value.amount == "12.50"
    assert total.status == "needs_review"
    assert "VALUE_NOT_IN_EVIDENCE" in {warning.code for warning in result.warnings}


def test_active_runs_do_not_starve_terminal_recovery(database, modules, monkeypatch):
    from app.extraction import service

    request = CreateExtractions(
        document_ids=[example_document().document_id],
        profile_id=example_profile().id,
        profile_version=1,
    )
    with database() as session:
        active = create_extractions(session, request).extractions[0].id
    with database() as session:
        stranded = create_extractions(session, request).extractions[0].id
    with database.begin() as session:
        session.execute(
            update(ExtractionRecord)
            .where(ExtractionRecord.id == active)
            .values(updated_at=func.now() - timedelta(minutes=10))
        )
        session.execute(
            update(Job)
            .where(Job.payload["resource_id"].astext == str(stranded))
            .values(status="failed", error_code="LEASE_EXHAUSTED")
        )
    monkeypatch.setattr(service, "RECOVERY_BATCH_SIZE", 1)
    for _ in range(2):
        with database() as session:
            recover_terminal_extractions(session)
    with database() as session:
        assert get_extraction(session, active).status == "queued"
        recovered = get_extraction(session, stranded)
        assert recovered.status == "failed"
        assert recovered.error.code == "EXTRACTION_INTERRUPTED"


def test_serialization_normalizes_database_timestamps_to_utc():
    created = datetime(2026, 10, 30, 15, 0, tzinfo=timezone(timedelta(hours=1)))
    record = ExtractionRecord(
        id=uuid4(),
        document_id=uuid4(),
        profile_id=uuid4(),
        profile_version=1,
        status="queued",
        mode="fixture",
        fields=[],
        tables=[],
        warnings=[],
        error=None,
        created_at=created,
    )
    result = to_dto(record)
    assert result.created_at == created.astimezone(UTC)
    assert result.created_at.utcoffset() == timedelta(0)


def test_ambiguous_dollar_symbol_does_not_verify_a_currency_guess():
    result = assembled("Total: $12.50", {"total": money("12.50", "USD", "u")})
    total = next(field for field in result.fields if field.key == "total")
    assert total.status == "needs_review"
    assert "CURRENCY_AMBIGUOUS" in {warning.code for warning in result.warnings}


def test_currency_prefix_does_not_hide_a_debit_sign():
    result = assembled("-$12.50", {"total": money("$12.50", "USD", "u")})
    assert "VALUE_NOT_IN_EVIDENCE" in {warning.code for warning in result.warnings}


def test_parenthesized_numeric_supplier_name_is_not_a_debit():
    result = assembled("Supplier: (12 Monkeys)", {"supplier": value("12 Monkeys", "u")})
    assert next(field for field in result.fields if field.key == "supplier").status == "found"


def test_batch_failure_rolls_back_earlier_documents_and_jobs(database, modules):
    from app.platform.errors import NotFoundError
    from sqlalchemy import select

    request = CreateExtractions(
        document_ids=[example_document().document_id, uuid4()],
        profile_id=example_profile().id,
        profile_version=1,
    )
    with database() as session, pytest.raises(NotFoundError):
        create_extractions(session, request)
    with database() as session:
        assert session.scalar(select(func.count()).select_from(ExtractionRecord)) == 0
        assert session.scalar(select(func.count()).select_from(Job)) == 0


def test_provider_uses_frozen_profile_without_holding_a_transaction(database, modules):
    from app.extraction.service import process_extraction
    from extraction_support import ScriptedProvider

    original = example_profile()
    request = CreateExtractions(
        document_ids=[example_document().document_id], profile_id=original.id, profile_version=1
    )
    with database() as session:
        queued = create_extractions(session, request).extractions[0]
    changed = original.model_copy(deep=True)
    changed.scalar_fields[0].key = "later_profile_change"
    modules.add_profile(changed)
    with database() as session:

        class Provider(ScriptedProvider):
            def extract(self, profile, options, document):
                assert not session.in_transaction()
                assert profile == original
                return super().extract(profile, options, document)

        process_extraction(session, queued.id, provider=Provider(reply_for(original)))
    with database() as session:
        assert get_extraction(session, queued.id).status == "ready"


def test_worker_failure_logs_preserve_correlation_and_redact_private_data(
    database, modules, captured_logs
):
    from app.extraction.service import process_extraction
    from app.platform.jobs import JobRegistry, run_once
    from app.platform.logging import request_id
    from extraction_support import ScriptedProvider

    secrets = [
        "sk-" + "synthetic" * 6,
        "Bearer private-test-header",
        "session=private-cookie",
        "Eva Synthetic",
        "SK3112000000198742637541",
        "12345.67",
        "private-invoice.pdf",
    ]
    provider = ScriptedProvider(RuntimeError(" ".join(secrets)))
    correlation = str(uuid4())
    token = request_id.set(correlation)
    try:
        with database() as session:
            queued = create_extractions(
                session,
                CreateExtractions(
                    document_ids=[example_document().document_id],
                    profile_id=example_profile().id,
                    profile_version=1,
                ),
            ).extractions[0]
    finally:
        request_id.reset(token)
    registry = JobRegistry()
    registry.register_handler(
        "extraction.process", lambda session, id: process_extraction(session, id, provider=provider)
    )
    for _ in range(3):
        assert run_once(database, registry)
        with database.begin() as session:
            session.execute(update(Job).values(available_at=func.now() - timedelta(seconds=1)))
    failure = next(record for record in captured_logs() if record["event"] == "extraction.failed")
    assert failure["requestId"] == correlation
    assert failure["extractionId"] == str(queued.id)
    assert failure["documentId"] == str(example_document().document_id)
    assert failure["level"] == "ERROR"
    assert failure["errorCode"] == "EXTRACTION_INTERNAL_ERROR"
    assert failure["attempt"] == 3 and failure["stack"]
    assert all(secret not in captured_logs.text() for secret in secrets)
    assert any(
        record["event"] == "job.retry_scheduled" and "jobId" in record for record in captured_logs()
    )


def test_explicit_currency_code_disambiguates_a_dollar_symbol():
    result = assembled("Total: $12.50 USD", {"total": money("12.50", "USD", "u")})
    assert next(field for field in result.fields if field.key == "total").status == "found"
