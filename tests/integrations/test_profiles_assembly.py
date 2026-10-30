import io
import json
import logging
from pathlib import Path

from app.main import create_app
from app.platform.logging import JsonFormatter, logger
from app.platform.routes import router as shell_router
from fastapi.testclient import TestClient


def test_production_profile_routes_persist_versions_and_safe_json_context(database):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    try:
        with TestClient(
            create_app(),
            base_url="http://localhost",
            headers={
                "Origin": "http://localhost:5173",
            },
        ) as client:
            source = json.loads(Path("contracts/examples/form.json").read_text())
            response = client.post(
                "/api/v1/forms", json={"name": "Assembly form", "definition": source}
            )
            assert response.status_code == 201
            form = response.json()["data"]
            definition = json.loads(Path("contracts/examples/profile.json").read_text())
            del definition["id"], definition["version"]
            definition["formId"] = form["id"]
            definition["name"] = "private profile name"
            created = client.post("/api/v1/profiles", json=definition)
            assert created.status_code == 201
            profile = created.json()["data"]
            versioned = client.post(
                f"/api/v1/profiles/{profile['id']}/versions",
                json={
                    **definition,
                    "expectedVersion": 1,
                    "name": "private changed label",
                },
            )
            assert versioned.status_code == 201
            assert versioned.json()["data"]["version"] == 2
            assert (
                client.get(f"/api/v1/profiles/{profile['id']}?version=1").json()["data"] == profile
            )
            assert client.get("/api/v1/profiles").json()["pagination"]["total"] == 1
            assert client.get("/api/v1/forms").json()["pagination"]["total"] == 1
            assert client.get(f"/api/v1/forms/{form['id']}").json()["data"] == form
        lines = [json.loads(line) for line in stream.getvalue().splitlines()]
        events = [line for line in lines if line["event"].startswith("profile.")]
        assert [line["event"] for line in events] == ["profile.created", "profile.version_created"]
        assert [line["version"] for line in events] == [1, 2]
        assert all(
            line["profileId"] == profile["id"] and line["formId"] == form["id"] for line in events
        )
        assert events[0]["requestId"] == created.headers["x-request-id"]
        assert events[1]["requestId"] == versioned.headers["x-request-id"]
        assert "private profile" not in stream.getvalue()
        assert "private changed" not in stream.getvalue()
    finally:
        logger.removeHandler(handler)


def test_profiles_have_no_unavailable_duplicate_shells():
    assert not any(route.path.startswith(("/forms", "/profiles")) for route in shell_router.routes)
    from app.platform.database import Base

    assert {"profile_forms", "profile_heads", "profile_versions"} <= Base.metadata.tables.keys()


def test_export_uses_real_pinned_profile_after_later_mapping_edit(database, monkeypatch):
    from copy import deepcopy

    from app.integrations import dependencies
    from app.platform.contracts import Extraction, Review

    root = Path("contracts/examples")
    extraction = Extraction.model_validate_json((root / "extraction.json").read_text())
    review = Review.model_validate_json((root / "review.json").read_text())
    # Only the two unreviewed/absent module reads are test doubles. Profile/form
    # reads below use the production public services and migrated PostgreSQL.
    monkeypatch.setattr(dependencies, "get_confirmed_review", lambda *args: review)
    monkeypatch.setattr(dependencies, "get_extraction", lambda *args: extraction)
    with TestClient(
        create_app(),
        base_url="http://localhost",
        headers={
            "Origin": "http://localhost:5173",
        },
    ) as client:
        form_response = client.post(
            "/api/v1/forms",
            json={
                "name": "Pinned mapping",
                "definition": json.loads((root / "form.json").read_text()),
            },
        )
        assert form_response.status_code == 201
        form = form_response.json()["data"]
        definition = json.loads((root / "profile.json").read_text())
        del definition["id"], definition["version"]
        definition["formId"] = form["id"]
        profile_response = client.post("/api/v1/profiles", json=definition)
        assert profile_response.status_code == 201
        profile = profile_response.json()["data"]
        from uuid import UUID

        extraction.profile_id = UUID(profile["id"])
        edited = deepcopy(definition)
        first, second = edited["scalarFields"][:2]
        first["targetTag"], second["targetTag"] = second["targetTag"], first["targetTag"]
        version = client.post(
            f"/api/v1/profiles/{profile['id']}/versions",
            json={
                **edited,
                "expectedVersion": 1,
            },
        )
        assert version.status_code == 201
        created = client.post(
            "/api/v1/submissions",
            headers={"Idempotency-Key": "pinned-mapping"},
            json={
                "reviewId": str(review.extraction_id),
                "reviewRevision": review.revision,
                "mode": "export",
                "targetContext": {"applicationId": None},
                "acknowledgeOverwrite": False,
            },
        )
        assert created.status_code == 201
        operation = created.json()["data"]
        attachment = client.get(f"/api/v1/submissions/{operation['id']}/export")
        assert attachment.status_code == 200
        payload = attachment.json()
        assert payload["profileId"] == profile["id"]
        assert payload["formId"] == form["id"]
        assert payload["profileVersion"] == 1
        values = {field["targetTag"]: field["value"] for field in payload["fields"]}
        assert values["invoice_number"] == "DEMO-2026-001"
        assert values["supplier"] == "Demo Paper s.r.o."
        assert values["purchase_order"] == "HUMAN-PO-001"
