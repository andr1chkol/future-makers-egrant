from uuid import UUID

import pytest
from app.main import create_app
from app.platform.settings import Settings, get_settings
from fastapi.testclient import TestClient
from pydantic import ValidationError


def test_fixture_no_provider_startup_and_unavailable_routes():
    with TestClient(create_app(), base_url="http://localhost") as client:
        result = client.get("/api/v1/capabilities")
        assert result.status_code == 200
        assert result.json()["data"] == {
            "ocrConfigured": False,
            "aiConfigured": False,
            "egrantConfigured": False,
            "mode": "fixture",
        }
        assert UUID(result.headers["x-request-id"])
        response = client.get("/api/v1/extractions")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "FEATURE_UNAVAILABLE"
        assert client.get("/api/v1/documents?limit=201").status_code == 422
        assert client.get("/api/v1/documents/invalid-id").status_code == 422


def test_bypass_rejects_non_local_request():
    with TestClient(create_app(), base_url="http://external.example") as client:
        assert client.get("/api/v1/documents").status_code == 401
        assert (
            client.get("/api/v1/documents/00000000-0000-4000-8000-000000000001/content").status_code
            == 401
        )


def test_live_requires_configured_gate(monkeypatch):
    monkeypatch.setenv("APP_MODE", "live")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_origin_required_and_validation_does_not_echo_secrets():
    with TestClient(create_app(), base_url="http://localhost") as client:
        response = client.post("/api/v1/auth/login", json={"accessCode": "secret"})
        assert response.status_code == 403
        response = client.post(
            "/api/v1/auth/login",
            json={"accessCode": {"secret": "PRIVATE"}},
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 422
        assert "PRIVATE" not in response.text


def test_durable_cookie_login_revocation_and_expiry(database, monkeypatch):
    from datetime import timedelta

    from app.platform.access import token_hash
    from app.platform.models import AccessSession
    from sqlalchemy import func, update

    monkeypatch.setenv("DEV_AUTH_BYPASS", "false")
    monkeypatch.setenv("ACCESS_CODE", "test-only-access-code-32-characters")
    get_settings.cache_clear()
    headers = {"Origin": "http://localhost:5173"}
    with TestClient(create_app(), base_url="http://localhost") as client:
        assert client.get("/api/v1/capabilities").status_code == 401
        assert (
            client.post(
                "/api/v1/auth/login", headers=headers, json={"accessCode": "incorrect"}
            ).status_code
            == 401
        )
        response = client.post(
            "/api/v1/auth/login",
            headers=headers,
            json={"accessCode": "test-only-access-code-32-characters"},
        )
        assert response.status_code == 200
        assert "HttpOnly" in response.headers["set-cookie"]
        assert "SameSite=strict" in response.headers["set-cookie"]
        cookie = client.cookies.get("egrant_session")
        with database() as session:
            assert session.get(AccessSession, cookie) is None
            assert session.get(AccessSession, token_hash(cookie))
        assert client.get("/api/v1/auth/session").status_code == 200
        # A new process/app instance accepts the same server-issued durable session.
        with TestClient(create_app(), base_url="http://localhost") as second:
            second.cookies.set("egrant_session", cookie, path="/api/v1")
            assert second.get("/api/v1/auth/session").status_code == 200
        assert client.delete("/api/v1/auth/session", headers=headers).status_code == 204
        client.cookies.set("egrant_session", cookie, path="/api/v1")
        assert client.get("/api/v1/auth/session").status_code == 401
        client.post(
            "/api/v1/auth/login",
            headers=headers,
            json={"accessCode": "test-only-access-code-32-characters"},
        )
        with database.begin() as session:
            session.execute(
                update(AccessSession).values(expires_at=func.now() - timedelta(seconds=1))
            )
        assert client.get("/api/v1/auth/session").status_code == 401


def test_settings_fail_closed_without_disclosing_inputs(monkeypatch):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "false")
    monkeypatch.setenv("ACCESS_CODE", "private-short-code")
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)
    assert "private-short-code" not in str(error.value)
    assert "input_value" not in str(error.value)


def test_capabilities_do_not_enable_unimplemented_adapters(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-provider-key")
    monkeypatch.setenv("OCR_API_KEY", "test-provider-key")
    monkeypatch.setenv("EGRANT_TOKEN", "test-provider-token")
    with TestClient(create_app(), base_url="http://localhost") as client:
        result = client.get("/api/v1/capabilities").json()["data"]
        assert not result["ocrConfigured"]
        assert not result["aiConfigured"]
        assert not result["egrantConfigured"]
