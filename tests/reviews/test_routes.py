import pytest
from app.main import create_app
from app.platform.contracts import Review
from app.reviews.routes import router
from fastapi.testclient import TestClient


@pytest.fixture
def client(review_database, review_context):
    app = create_app()
    # Assemble only this module while retaining the real middleware and error handlers.
    app.router.routes.clear()
    app.include_router(router, prefix="/api/v1")
    with TestClient(
        app, base_url="http://localhost", headers={"Origin": "http://localhost:5173"}
    ) as client:
        yield client


def test_real_http_draft_confirmation_and_access(client, review_context, corrected_snapshot):
    path = f"/api/v1/reviews/{review_context[0].id}"
    response = client.get(path)
    assert response.status_code == 200
    assert Review.model_validate(response.json()["data"]).revision == 0
    result = client.put(path, json={"expectedRevision": 0, **corrected_snapshot})
    assert result.status_code == 200 and result.json()["data"]["revision"] == 1
    assert client.put(path, json={"expectedRevision": 0, **corrected_snapshot}).status_code == 409
    result = client.post(path + "/confirm", json={"expectedRevision": 1})
    assert result.status_code == 200 and result.json()["data"]["status"] == "confirmed"
    assert client.post(path + "/confirm", json={"expectedRevision": 2}).json() == result.json()
    assert client.post(path + "/confirm", json={"expectedRevision": 1}).status_code == 409
    assert client.put(path, json={"expectedRevision": 2, **corrected_snapshot}).status_code == 409
    assert client.get(path, headers={"Host": "outside.invalid"}).status_code == 401
    assert (
        client.post(
            path + "/confirm",
            json={"expectedRevision": 2},
            headers={"Origin": "https://untrusted.invalid"},
        ).status_code
        == 403
    )
    assert client.get("/api/v1/reviews/not-uuid").status_code == 422
