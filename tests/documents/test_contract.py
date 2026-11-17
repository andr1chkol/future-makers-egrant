import json
from pathlib import Path

import jsonschema
import pytest
import yaml
from app.documents.normalization import MEDIA_TYPES


@pytest.mark.parametrize(
    ("filename", "media", "fixture"),
    [
        ("text.pdf", "application/pdf", "text_pdf"),
        ("photo.png", "image/png", "png_content"),
        ("data.csv", "text/csv", "csv_content"),
    ],
)
def test_upload_and_detail_match_frozen_json_schema(client, filename, media, fixture, request):
    content = request.getfixturevalue(fixture)
    response = client.post("/api/v1/documents", files=[("files", (filename, content, media))])
    assert response.status_code == 201
    root = Path(__file__).resolve().parents[2]
    schema = yaml.safe_load((root / "contracts/api.yaml").read_text(encoding="utf-8"))
    document_schema = {
        "$ref": "#/components/schemas/Success_list_Document__",
        "components": schema["components"],
    }
    jsonschema.validate(response.json(), document_schema)
    document_id = response.json()["data"][0]["id"]
    detail = client.get(f"/api/v1/documents/{document_id}")
    assert detail.status_code == 200
    jsonschema.validate(
        detail.json(),
        {"$ref": "#/components/schemas/Success_Document_", "components": schema["components"]},
    )


def test_module_openapi_matches_frozen_document_operations(client):
    root = Path(__file__).resolve().parents[2]
    frozen = yaml.safe_load((root / "contracts/api.yaml").read_text(encoding="utf-8"))
    actual = client.app.openapi()
    for path, operations in frozen["paths"].items():
        if not path.startswith("/api/v1/documents"):
            continue
        assert actual["paths"][path] == operations


def test_shared_examples_are_reference_data_not_a_live_fallback(client):
    root = Path(__file__).resolve().parents[2]
    example = json.loads((root / "contracts/examples/document.json").read_text(encoding="utf-8"))
    assert client.get(f"/api/v1/documents/{example['id']}").status_code == 404
    assert client.get("/api/v1/documents").json()["data"] == []
    assert MEDIA_TYPES[".csv"] == "text/csv"
