import json
from pathlib import Path

import pytest
from app.platform.contracts import Extraction, FormDefinition, Profile
from app.reviews import service


@pytest.fixture
def review_database(database):
    return database


@pytest.fixture
def review_context(monkeypatch):
    root = Path("contracts/examples")
    extraction = Extraction.model_validate_json((root / "extraction.json").read_text())
    profile = Profile.model_validate_json((root / "profile.json").read_text())
    form = FormDefinition.model_validate_json((root / "form.json").read_text())
    monkeypatch.setattr(service, "load_context", lambda session, id: (extraction, profile, form))
    return extraction, profile, form


@pytest.fixture
def corrected_snapshot():
    value = json.loads(Path("contracts/examples/review.json").read_text())
    return {key: value[key] for key in ("fields", "tables", "acknowledgedWarnings")}
