"""Public assembled workflow using PostgreSQL and the production worker in fixture mode."""

import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from app.main import create_app
from app.platform.contracts import Warning, warning_identity
from app.platform.settings import get_settings
from fastapi.testclient import TestClient

EXAMPLES = Path("contracts/examples")


def wait_for_resource(client, path, status, worker):
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        assert worker.poll() is None, "Production worker exited before processing completed"
        response = client.get(path)
        assert response.status_code == 200, response.text
        resource = response.json()["data"]
        if resource["status"] == status:
            return resource
        assert resource["status"] != "failed", resource
        time.sleep(0.1)
    pytest.fail(f"Timed out waiting for {path} to become {status}: {resource}")


@contextmanager
def production_worker(tmp_path):
    with (tmp_path / "worker.log").open("a") as log:
        worker = subprocess.Popen(
            [sys.executable, "-m", "app.worker"],
            env={**os.environ, "PYTHONPATH": "backend"},
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            yield worker
        finally:
            worker.terminate()
            try:
                worker.wait(timeout=10)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=5)


@pytest.fixture
def full_product_client(database, monkeypatch, tmp_path):
    monkeypatch.setenv("FILE_STORAGE_PATH", str(tmp_path / "files"))
    get_settings.cache_clear()
    with TestClient(
        create_app(),
        base_url="http://localhost",
        headers={"Origin": "http://localhost:5173"},
    ) as client:
        yield client


@pytest.mark.parametrize("prefix", ["", "alternate_"])
def test_public_fixture_flow_preserves_human_values(full_product_client, tmp_path, prefix):
    with production_worker(tmp_path) as worker:
        exercise_public_flow(full_product_client, worker, prefix)


def configure_profile(client, prefix):
    source = json.loads((EXAMPLES / "form.json").read_text())
    for field in source["fields"]:
        field["tag"] = prefix + field["tag"]
    for table in source["tables"]:
        table["tag"] = prefix + table["tag"]
        for column in table["columns"]:
            column["tag"] = prefix + column["tag"]
    result = client.post("/api/v1/forms", json={"name": "Fixture acceptance", "definition": source})
    assert result.status_code == 201, result.text
    form = result.json()["data"]
    assert form["originalJson"] == source
    assert form["isIllustrative"] is True
    definition = json.loads((EXAMPLES / "profile.json").read_text())
    del definition["id"], definition["version"]
    definition["formId"] = form["id"]
    for field in definition["scalarFields"]:
        field["targetTag"] = prefix + field["targetTag"]
    for table in definition["tableFields"]:
        table["targetTag"] = prefix + table["targetTag"]
        for column in table["columns"]:
            column["targetTag"] = prefix + column["targetTag"]
    response = client.post("/api/v1/profiles", json=definition)
    assert response.status_code == 201, response.text
    profile = response.json()["data"]
    return form, profile, definition


def exercise_public_flow(client, worker, prefix):
    form, profile, definition = configure_profile(client, prefix)
    original = (EXAMPLES / "synthetic-invoice.csv").read_bytes()
    documents = []
    for _ in range(2):
        response = client.post(
            "/api/v1/documents", files={"files": ("synthetic-invoice.csv", original, "text/csv")}
        )
        assert response.status_code == 201, response.text
        documents.append(response.json()["data"][0])
    assert documents[1]["id"] != documents[0]["id"]
    assert documents[1]["duplicateOf"] == documents[0]["id"]
    assert documents[0]["contentHash"] == sha256(original).hexdigest()
    for document in documents:
        wait_for_resource(client, f"/api/v1/documents/{document['id']}", "ready", worker)
        assert client.get(f"/api/v1/documents/{document['id']}/content").content == original
    document_id = documents[0]["id"]
    normalized = client.get(f"/api/v1/documents/{document_id}/normalized").json()["data"]
    assert len(normalized["units"]) == 23
    units = {unit["id"]: unit for unit in normalized["units"]}
    response = client.post(
        "/api/v1/extractions",
        json={"documentIds": [document_id], "profileId": profile["id"], "profileVersion": 1},
    )
    assert response.status_code == 202, response.text
    extraction_id = response.json()["data"]["extractions"][0]["id"]
    extraction = wait_for_resource(client, f"/api/v1/extractions/{extraction_id}", "ready", worker)
    assert extraction["mode"] == "fixture"
    fields = {field["key"]: field for field in extraction["fields"]}
    assert fields["purchase_order"]["value"] is None
    assert fields["purchase_order"]["status"] == "missing"
    sources = [source for field in extraction["fields"] for source in field["sources"]]
    sources += [
        source
        for table in extraction["tables"]
        for row in table["rows"]
        for cell in row["cells"]
        for source in cell["sources"]
    ]
    assert sources
    for source in sources:
        unit = units[source["unitId"]]
        assert source["documentId"] == document_id
        assert source["quote"] is None or source["quote"] in unit["text"]
        assert all(source[key] == unit[key] for key in ("page", "sheet", "cell"))
    duplicate_response = client.post(
        "/api/v1/extractions",
        json={"documentIds": [documents[1]["id"]], "profileId": profile["id"], "profileVersion": 1},
    )
    assert duplicate_response.status_code == 202, duplicate_response.text
    duplicate_id = duplicate_response.json()["data"]["extractions"][0]["id"]
    duplicate_extraction = wait_for_resource(
        client, f"/api/v1/extractions/{duplicate_id}", "ready", worker
    )
    assert duplicate_extraction["documentId"] == documents[1]["id"]
    assert duplicate_id != extraction_id
    later_definition = deepcopy(definition)
    first, second = later_definition["scalarFields"][:2]
    first["targetTag"], second["targetTag"] = second["targetTag"], first["targetTag"]
    versioned = client.post(
        f"/api/v1/profiles/{profile['id']}/versions",
        json={**later_definition, "expectedVersion": 1, "name": "Later manager edit"},
    )
    assert versioned.status_code == 201, versioned.text
    assert client.get(f"/api/v1/profiles/{profile['id']}?version=1").json()["data"] == profile
    review = client.get(f"/api/v1/reviews/{extraction_id}").json()["data"]
    assert review["status"] == "draft"
    draft = {key: deepcopy(review[key]) for key in ("fields", "tables", "acknowledgedWarnings")}
    draft["acknowledgedWarnings"] = [
        warning_identity(Warning.model_validate(warning)) for warning in extraction["warnings"]
    ]
    for field in draft["fields"]:
        if field["key"] == "buyer":
            field["value"] = None
    saved = client.put(
        f"/api/v1/reviews/{extraction_id}", json={**draft, "expectedRevision": review["revision"]}
    )
    assert saved.status_code == 200, saved.text
    revision = saved.json()["data"]["revision"]
    blocked = client.post(
        f"/api/v1/reviews/{extraction_id}/confirm", json={"expectedRevision": revision}
    )
    assert blocked.status_code == 422, blocked.text
    values = {
        "invoice_number": "HUMAN-INVOICE-002",
        "buyer": "Human-reviewed buyer",
        "purchase_order": "HUMAN-PO-002",
        "total": {"amount": "60.00", "currency": "EUR"},
    }
    for field in draft["fields"]:
        if field["key"] in values:
            field["value"] = values[field["key"]]
    assert len(draft["tables"][0]["rows"]) == 2
    for index, row in enumerate(draft["tables"][0]["rows"]):
        replacements = {
            "description": f"Human-reviewed row {index + 1}",
            "quantity": "3.00",
            "unit_price": {"amount": "10.00", "currency": "EUR"},
            "line_total": {"amount": "30.00", "currency": "EUR"},
        }
        for cell in row["cells"]:
            cell["value"] = replacements[cell["key"]]
    saved = client.put(
        f"/api/v1/reviews/{extraction_id}", json={**draft, "expectedRevision": revision}
    )
    assert saved.status_code == 200, saved.text
    assert (
        client.put(
            f"/api/v1/reviews/{extraction_id}", json={**draft, "expectedRevision": revision}
        ).status_code
        == 409
    )
    reloaded = client.get(f"/api/v1/reviews/{extraction_id}").json()["data"]
    assert reloaded == saved.json()["data"]
    assert reloaded["status"] == "draft"
    assert reloaded["fields"] == draft["fields"]
    assert reloaded["tables"] == draft["tables"]
    confirmed = client.post(
        f"/api/v1/reviews/{extraction_id}/confirm",
        json={"expectedRevision": reloaded["revision"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    confirmed = confirmed.json()["data"]
    assert confirmed["status"] == "confirmed"
    assert (
        client.post(
            f"/api/v1/reviews/{extraction_id}/confirm",
            json={"expectedRevision": confirmed["revision"]},
        ).json()["data"]
        == confirmed
    )
    body = {
        "reviewId": extraction_id,
        "reviewRevision": confirmed["revision"],
        "mode": "export",
        "targetContext": {"applicationId": None},
        "acknowledgeOverwrite": False,
    }
    headers = {"Idempotency-Key": "full-product-export"}
    response = client.post("/api/v1/submissions", headers=headers, json=body)
    assert response.status_code == 201, response.text
    submission = response.json()["data"]
    assert (
        client.post("/api/v1/submissions", headers=headers, json=body).json()["data"] == submission
    )
    assert (
        client.post(
            "/api/v1/submissions",
            headers=headers,
            json={**body, "reviewRevision": confirmed["revision"] - 1},
        ).status_code
        == 409
    )
    download = client.get(f"/api/v1/submissions/{submission['id']}/export")
    assert download.status_code == 200, download.text
    assert "attachment" in download.headers["content-disposition"]
    payload = download.json()
    assert payload["profileVersion"] == 1
    assert payload["formId"] == form["id"]
    assert payload["profileId"] == profile["id"]
    assert payload["fields"] == [
        {"targetTag": prefix + field["key"], "value": field["value"]} for field in draft["fields"]
    ]
    assert payload["tables"] == [
        {
            "targetTag": prefix + "items",
            "writeMode": "append",
            "rows": [
                {
                    "rowId": row["rowId"],
                    "values": {prefix + cell["key"]: cell["value"] for cell in row["cells"]},
                }
                for row in draft["tables"][0]["rows"]
            ],
        }
    ]
    assert client.get(f"/api/v1/submissions/{submission['id']}/export").json() == payload
    assert client.get(f"/api/v1/extractions/{extraction_id}").json()["data"] == extraction


def test_worker_restart_preserves_queued_work_and_fixture_miss_stays_failed(
    full_product_client, tmp_path
):
    client = full_product_client
    _, profile, _ = configure_profile(client, "")
    response = client.post(
        "/api/v1/documents",
        files={"files": ("unrecorded.csv", b"key,value\nUnknown,999\n", "text/csv")},
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["data"][0]["id"]
    with production_worker(tmp_path) as worker:
        wait_for_resource(client, f"/api/v1/documents/{document_id}", "ready", worker)
    response = client.post(
        "/api/v1/extractions",
        json={"documentIds": [document_id], "profileId": profile["id"], "profileVersion": 1},
    )
    assert response.status_code == 202, response.text
    extraction_id = response.json()["data"]["extractions"][0]["id"]
    path = f"/api/v1/extractions/{extraction_id}"
    assert client.get(path).json()["data"]["status"] == "queued"
    with production_worker(tmp_path) as restarted:
        failed = wait_for_resource(client, path, "failed", restarted)
        assert failed["error"]["code"] == "FIXTURE_NOT_AVAILABLE"
        assert failed["fields"] == []
        assert failed["tables"] == []
        assert client.get(f"/api/v1/reviews/{extraction_id}").status_code == 409
        retried = client.post(f"{path}/retries")
        assert retried.status_code == 202, retried.text
        assert retried.json()["data"]["id"] == extraction_id
        failed_again = wait_for_resource(client, path, "failed", restarted)
        assert failed_again["error"]["code"] == "FIXTURE_NOT_AVAILABLE"
        assert failed_again["id"] == extraction_id
        assert failed_again["fields"] == []
        assert failed_again["tables"] == []
