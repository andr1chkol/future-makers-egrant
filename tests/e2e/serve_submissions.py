"""Test-only neighboring interfaces; the submission HTTP API and PostgreSQL are real."""

import os
import subprocess
import sys
from pathlib import Path

import uvicorn
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
url = os.environ["INTEGRATION_E2E_DATABASE_URL"]
if not (make_url(url).database or "").startswith("egrant_test_e2e"):
    raise RuntimeError("Dedicated egrant_test_e2e database required")
os.environ.update(
    DATABASE_URL=url,
    APP_MODE="fixture",
    DEV_AUTH_BYPASS="true",
    COOKIE_SECURE="false",
    PUBLIC_ORIGIN="http://localhost:5176",
)
with create_engine(url, hide_parameters=True).begin() as connection:
    connection.execute(text("DROP SCHEMA public CASCADE"))
    connection.execute(text("CREATE SCHEMA public"))
subprocess.run(
    [str(ROOT / ".venv/bin/alembic"), "-c", "backend/alembic.ini", "upgrade", "head"],
    cwd=ROOT,
    check=True,
)

from app.integrations import dependencies  # noqa: E402
from app.main import create_app  # noqa: E402
from app.platform import contracts as c  # noqa: E402
from app.platform.errors import ConflictError, NotFoundError  # noqa: E402

examples = ROOT / "contracts/examples"
review = c.Review.model_validate_json((examples / "review.json").read_text())
extraction = c.Extraction.model_validate_json((examples / "extraction.json").read_text())
profile = c.Profile.model_validate_json((examples / "profile.json").read_text())
form = c.FormDefinition.model_validate_json((examples / "form.json").read_text())


def confirmed(session, id, revision):
    if id != review.extraction_id:
        raise NotFoundError()
    if revision != review.revision:
        raise ConflictError()
    return review


# Only the test server installs these public-interface doubles. Production
# imports missing modules as unavailable and never loads these example records.
dependencies.get_confirmed_review = confirmed
dependencies.get_extraction = lambda *args: extraction
dependencies.get_profile = lambda *args: profile
dependencies.get_form = lambda *args: form
uvicorn.run(create_app(), host="127.0.0.1", port=8013, access_log=False)
