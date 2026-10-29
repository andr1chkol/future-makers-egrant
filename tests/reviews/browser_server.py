"""Test-only neighboring adapters around the real review API and PostgreSQL.

Never imported by production startup. No provider or external application writes.
"""

import json
import os
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from app.main import create_app
from app.platform.contracts import CreateSubmission, Extraction, FormDefinition, Profile
from app.platform.database import session_factory
from app.platform.errors import ConflictError, UnavailableError
from app.platform.settings import get_settings
from app.reviews import service
from app.reviews.models import ReviewRecord, ReviewRevision
from app.reviews.routes import router
from fastapi import Header
from sqlalchemy import create_engine, delete, text
from sqlalchemy.engine import make_url

url = os.environ["TEST_DATABASE_URL"]
if not (make_url(url).database or "").startswith("egrant_test"):
    raise RuntimeError("Browser tests require an isolated egrant_test database")
os.environ["DATABASE_URL"] = url
get_settings.cache_clear()
engine = create_engine(url, hide_parameters=True)
with engine.begin() as connection:
    connection.execute(text("DROP SCHEMA public CASCADE"))
    connection.execute(text("CREATE SCHEMA public"))
config = Config("backend/alembic.ini")
config.set_main_option(
    "version_locations", "backend/migrations/versions backend/app/reviews/migrations"
)
command.upgrade(config, "0401_reviews")

root = Path("contracts/examples")
examples = {file.stem: json.loads(file.read_text()) for file in root.glob("*.json")}
extraction = Extraction.model_validate(examples["extraction"])
profile = Profile.model_validate(examples["profile"])
form = FormDefinition.model_validate(examples["form"])
service.load_context = lambda session, id: (extraction, profile, form)
app = create_app()
app.router.routes.clear()
app.include_router(router, prefix="/api/v1")
submissions: dict[str, dict] = {}


@app.get("/health")
def health():
    return {"data": {"status": "ok"}}


@app.get("/api/v1/auth/session")
def session_info():
    return {"data": {"authenticated": True, "mode": "fixture"}}


@app.get("/api/v1/capabilities")
def capabilities():
    return {
        "data": {
            "mode": "fixture",
            "ocrConfigured": False,
            "aiConfigured": False,
            "egrantConfigured": False,
        }
    }


@app.get("/api/v1/extractions/{id}")
def get_extraction(id: UUID):
    if id != extraction.id:
        raise ConflictError()
    return {"data": examples["extraction"]}


@app.get("/api/v1/profiles/{id}")
def get_profile(id: UUID, version: int):
    return {"data": examples["profile"]}


@app.get("/api/v1/forms/{id}")
def get_form(id: UUID):
    return {"data": examples["form"]}


@app.get("/api/v1/documents/{id}")
def get_document(id: UUID):
    return {"data": examples["document"]}


@app.get("/api/v1/documents/{id}/normalized")
def get_normalized(id: UUID):
    return {"data": examples["normalized-document"]}


@app.post("/api/v1/submissions")
def create_export(request: CreateSubmission, idempotency_key: str = Header()):
    if request.mode != "export":
        raise UnavailableError()
    if idempotency_key in submissions:
        return {"data": submissions[idempotency_key]}
    with session_factory()() as session:
        confirmed = service.get_confirmed_review(
            session, request.review_id, request.review_revision
        )
    # This fake integration consumes the public immutable review, never the AI extraction.
    submission = json.loads(json.dumps(examples["submission"]))
    submission["id"] = str(uuid4())
    submission["reviewRevision"] = confirmed.revision
    submission["payload"]["fields"] = [
        {
            "targetTag": definition.target_tag,
            "value": next(field.value for field in confirmed.fields if field.key == definition.key),
        }
        for definition in profile.scalar_fields
    ]
    submission["payload"]["tables"] = [
        {
            "targetTag": definition.target_tag,
            "writeMode": definition.write_mode,
            "rows": [
                {
                    "rowId": str(row.row_id),
                    "values": {
                        column.target_tag: next(
                            cell.model_dump(mode="json")["value"]
                            for cell in row.cells
                            if cell.key == column.key
                        )
                        for column in definition.columns
                    },
                }
                for row in next(
                    table.rows for table in confirmed.tables if table.key == definition.key
                )
            ],
        }
        for definition in profile.table_fields
    ]
    from fastapi.encoders import jsonable_encoder

    submissions[idempotency_key] = jsonable_encoder(submission)
    return {"data": submissions[idempotency_key]}


@app.get("/api/v1/submissions/{id}/export")
def download_export(id: UUID):
    submission = next(item for item in submissions.values() if item["id"] == str(id))
    return submission["payload"]


@app.post("/api/v1/__test/reset")
def reset_reviews():
    with session_factory().begin() as session:
        session.execute(delete(ReviewRevision))
        session.execute(delete(ReviewRecord))
    submissions.clear()
    return {"data": {"mode": "fixture"}}
