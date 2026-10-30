from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient


@pytest.fixture
def profiles_database(database):
    command.upgrade(Config("backend/app/profiles/alembic.ini"), "head")
    return database


@pytest.fixture
def client(profiles_database, monkeypatch):
    from app import main
    from app.profiles.routes import router

    # Supply the module router before assembly; lazy includes cannot be removed by route.path.
    monkeypatch.setattr(main, "router", router)
    app = main.create_app()
    with TestClient(
        app, base_url="http://localhost", headers={"origin": "http://localhost:5173"}
    ) as test_client:
        yield test_client


@pytest.fixture
def form_payload():
    import json

    return {
        "name": "Invoice form",
        "definition": json.loads(Path("contracts/examples/form.json").read_text()),
    }


@pytest.fixture
def profile_payload():
    import json

    value = json.loads(Path("contracts/examples/profile.json").read_text())
    del value["id"], value["version"]
    return value
