import hashlib
import json
from pathlib import Path

import jsonschema
import pytest
import yaml
from app.main import create_app
from app.platform import contracts as c
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "contracts/examples"
MODELS = {
    "form": c.FormDefinition,
    "profile": c.Profile,
    "document": c.Document,
    "normalized-document": c.NormalizedDocument,
    "extraction": c.Extraction,
    "review": c.Review,
    "submission": c.Submission,
}


def example(name):
    return json.loads((EXAMPLES / f"{name}.json").read_text())


@pytest.mark.parametrize("name,model", MODELS.items())
def test_examples_validate_against_dto_and_json_schema(name, model):
    value = example(name)
    model.model_validate(value)
    jsonschema.validate(value, model.model_json_schema(by_alias=True))


def test_examples_match_actual_invoice_and_human_correction():
    document = example("document")
    content = (EXAMPLES / document["filename"]).read_bytes()
    assert hashlib.sha256(content).hexdigest() == document["contentHash"]
    extraction = c.Extraction.model_validate(example("extraction"))
    normalized = c.NormalizedDocument.model_validate(example("normalized-document"))
    units = {unit.id: unit for unit in normalized.units}
    assert [unit.text for unit in normalized.units] == content.decode().splitlines()
    for field in extraction.fields + [
        cell for t in extraction.tables for r in t.rows for cell in r.cells
    ]:
        for source in field.sources:
            assert source.document_id == normalized.document_id
            assert source.quote in units[source.unit_id].text
    review = c.Review.model_validate(example("review"))
    assert review.acknowledged_warnings == [c.warning_identity(extraction.warnings[0])]
    assert next(f for f in extraction.fields if f.key == "purchase_order").value is None
    assert next(f for f in review.fields if f.key == "purchase_order").value == "HUMAN-PO-001"
    submission = c.Submission.model_validate(example("submission"))
    assert {f.target_tag: f.value for f in submission.payload.fields} == {
        f.key: f.value for f in review.fields
    }
    assert submission.review_revision == review.revision
    assert submission.payload.tables[0].rows[0].values == {
        c.key: c.value for c in review.tables[0].rows[0].cells
    }


def test_warning_acknowledgements_distinguish_locations_and_message():
    warning = c.Warning(code="MISSING", message="Value missing", field_key="first")
    identities = {
        c.warning_identity(warning),
        c.warning_identity(warning.model_copy(update={"field_key": "second"})),
        c.warning_identity(warning.model_copy(update={"message": "Other warning"})),
    }
    assert len(identities) == 3


def test_committed_openapi_matches_current_contract():
    assert yaml.safe_load((ROOT / "contracts/api.yaml").read_text()) == create_app().openapi()
    schema = create_app().openapi()
    assert set(schema["paths"]) == {
        "/health",
        "/api/v1/auth/login",
        "/api/v1/auth/session",
        "/api/v1/capabilities",
        "/api/v1/documents",
        "/api/v1/documents/{id}",
        "/api/v1/documents/{id}/content",
        "/api/v1/documents/{id}/normalized",
        "/api/v1/documents/{id}/retries",
        "/api/v1/forms",
        "/api/v1/forms/{id}",
        "/api/v1/profiles",
        "/api/v1/profiles/{id}",
        "/api/v1/profiles/{id}/versions",
        "/api/v1/extractions",
        "/api/v1/extractions/{id}",
        "/api/v1/extractions/{id}/retries",
        "/api/v1/reviews/{extraction_id}",
        "/api/v1/reviews/{extraction_id}/confirm",
        "/api/v1/submissions",
        "/api/v1/submissions/{id}",
        "/api/v1/submissions/{id}/export",
    }
    upload = schema["paths"]["/api/v1/documents"]["post"]
    assert "multipart/form-data" in upload["requestBody"]["content"]
    submission = schema["paths"]["/api/v1/submissions"]["post"]
    assert {"201", "202", "409", "503"} <= submission["responses"].keys()


@pytest.mark.parametrize(
    "field_type,value",
    [("decimal", 1.1), ("boolean", "true"), ("date", "2026-02-30"), ("money", "55.00")],
)
def test_extraction_rejects_incorrect_typed_values(field_type, value):
    with pytest.raises(ValidationError):
        c.ExtractedField(key="x", type=field_type, value=value, status="found", sources=[])


def test_team_contract_copies_stay_in_sync():
    for filename in ["CONTRACT.md", "QUALITY.md"]:
        assert (ROOT / filename).read_bytes() == (ROOT / "docs/team" / filename).read_bytes()


def test_openapi_protects_every_domain_route():
    schema = create_app().openapi()
    assert schema["components"]["securitySchemes"]["APIKeyCookie"] == {
        "type": "apiKey",
        "in": "cookie",
        "name": "egrant_session",
    }
    for path, operations in schema["paths"].items():
        if path in {"/health", "/api/v1/auth/login"}:
            continue
        for operation in operations.values():
            assert operation["security"] == [{"APIKeyCookie": []}]


def test_export_attachment_has_an_exact_payload_schema():
    operation = create_app().openapi()["paths"]["/api/v1/submissions/{id}/export"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SubmissionPayload"
    }
    assert "Content-Disposition" in operation["responses"]["200"]["headers"]
