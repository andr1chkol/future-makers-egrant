import copy
import json
from pathlib import Path
from uuid import uuid4

import jsonschema
import pytest
import yaml
from app.platform.contracts import FormDefinition, Page, Profile, Success


def make_profile(client, form_payload, profile_payload):
    response = client.post("/api/v1/forms", json=form_payload)
    assert response.status_code == 201
    form = response.json()["data"]
    profile_payload["formId"] = form["id"]
    response = client.post("/api/v1/profiles", json=profile_payload)
    assert response.status_code == 201
    return form, response.json()["data"]


def test_import_create_list_detail_versions_and_frozen_contract(
    client, form_payload, profile_payload
):
    form, profile = make_profile(client, form_payload, profile_payload)
    assert form["originalJson"] == form_payload["definition"]
    profile_payload["name"] = "Changed display label"
    changed = client.post(
        f"/api/v1/profiles/{profile['id']}/versions",
        json={
            **profile_payload,
            "expectedVersion": 1,
        },
    )
    assert changed.status_code == 201
    assert changed.json()["data"]["version"] == 2
    responses = [
        (f"/api/v1/forms/{form['id']}", Success[FormDefinition]),
        (f"/api/v1/profiles/{profile['id']}", Success[Profile]),
        (f"/api/v1/profiles/{profile['id']}?version=1", Success[Profile]),
        ("/api/v1/forms?limit=1&offset=0", Page[FormDefinition]),
        ("/api/v1/profiles?limit=1&offset=0", Page[Profile]),
    ]
    for url, model in responses:
        response = client.get(url)
        assert response.status_code == 200
        model.model_validate(response.json())
        jsonschema.validate(response.json(), model.model_json_schema(by_alias=True))
    assert client.get(f"/api/v1/profiles/{profile['id']}?version=1").json()["data"] == profile
    listing = client.get("/api/v1/profiles").json()
    assert listing["pagination"] == {"limit": 50, "offset": 0, "total": 1}
    assert listing["data"][0]["version"] == 2
    assert client.get("/api/v1/forms?offset=1").json()["data"] == []
    stale = client.post(
        f"/api/v1/profiles/{profile['id']}/versions",
        json={
            **profile_payload,
            "expectedVersion": 1,
        },
    )
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "CONFLICT"


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/forms?limit=0",
        "/api/v1/forms?limit=201",
        "/api/v1/forms?offset=-1",
        "/api/v1/profiles?limit=0",
        "/api/v1/profiles?offset=-1",
        "/api/v1/profiles/not-a-uuid",
        "/api/v1/forms/not-a-uuid",
        f"/api/v1/profiles/{uuid4()}?version=0",
    ],
)
def test_routes_reject_invalid_pagination_ids_and_versions(client, url):
    response = client.get(url)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_not_found_and_invalid_mappings_are_safe_and_local(client, form_payload, profile_payload):
    _, profile = make_profile(client, form_payload, profile_payload)
    for url in [
        f"/api/v1/forms/{uuid4()}",
        f"/api/v1/profiles/{uuid4()}",
        f"/api/v1/profiles/{profile['id']}?version=99",
    ]:
        assert client.get(url).status_code == 404
    broken = copy.deepcopy(profile_payload)
    broken["scalarFields"][0]["targetTag"] = "private-customer-name"
    response = client.post("/api/v1/profiles", json=broken)
    assert response.status_code == 422
    assert response.json()["error"]["details"] == {
        "fields": [
            {
                "path": "scalarFields.0.targetTag",
                "code": "DESTINATION_NOT_FOUND",
            }
        ]
    }
    assert "private-customer-name" not in response.text
    duplicate = copy.deepcopy(profile_payload)
    duplicate["scalarFields"].append(duplicate["scalarFields"][0])
    assert client.post("/api/v1/profiles", json=duplicate).status_code == 422
    missing_form = {**profile_payload, "formId": str(uuid4())}
    assert client.post("/api/v1/profiles", json=missing_form).status_code == 404


def test_invalid_and_hostile_json_is_data_never_logged_or_executed(client, form_payload):
    for content in [b'{"name": "private-value",', b"[]", b"null"]:
        response = client.post(
            "/api/v1/forms", content=content, headers={"content-type": "application/json"}
        )
        assert response.status_code == 422
        assert "private-value" not in response.text
    form_payload["definition"]["fields"][0]["label"] = "<script>private-value</script>"
    response = client.post("/api/v1/forms", json=form_payload)
    assert response.status_code == 201
    assert response.json()["data"]["fields"][0]["label"] == "<script>private-value</script>"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"


def test_module_routes_share_access_gate_and_origin_checks(client, form_payload, monkeypatch):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "false")
    monkeypatch.setenv("ACCESS_CODE", "a-valid-test-code-longer-than-24")
    from app.platform.settings import get_settings

    get_settings.cache_clear()
    for url in ["/api/v1/forms", "/api/v1/profiles", f"/api/v1/forms/{uuid4()}"]:
        assert client.get(url).status_code == 401
    assert client.post("/api/v1/forms", json=form_payload).status_code == 401
    assert (
        client.post(
            "/api/v1/forms", json=form_payload, headers={"origin": "https://untrusted.invalid"}
        ).status_code
        == 403
    )


def test_registered_module_schemas_match_frozen_request_and_response_models(client):
    frozen = yaml.safe_load(Path("contracts/api.yaml").read_text())
    actual = client.app.openapi()
    for path in [
        "/api/v1/forms",
        "/api/v1/forms/{id}",
        "/api/v1/profiles",
        "/api/v1/profiles/{id}",
        "/api/v1/profiles/{id}/versions",
    ]:
        for method, operation in actual["paths"][path].items():
            expected = frozen["paths"][path][method]
            assert operation.get("requestBody") == expected.get("requestBody")
            for status in ("200", "201"):
                if status in operation["responses"]:
                    assert operation["responses"][status] == expected["responses"][status]
            assert operation["security"] == [{"APIKeyCookie": []}]


@pytest.mark.parametrize(
    "name,code",
    [
        ("Bad\x00name", "INVALID_JSON"),
        ("Bad\ud800name", "VALIDATION_ERROR"),
    ],
)
def test_invalid_name_encoding_is_a_safe_validation_error(client, form_payload, name, code):
    form_payload["name"] = name
    response = client.post(
        "/api/v1/forms",
        content=json.dumps(form_payload),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
