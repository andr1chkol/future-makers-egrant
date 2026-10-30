"""Browser-test assembly of the shared app; neighboring modules are explicit fixture routes."""

import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import uvicorn
from alembic import command
from app.documents.ocr import ocr_configured
from app.documents.service import get_normalized, process_document
from app.platform.access import require_access
from app.platform.contracts import (
    CreateExtractions,
    Extraction,
    ExtractionBatch,
    Page,
    Profile,
    QueuedExtraction,
    Success,
)
from app.platform.jobs import JobRegistry, run_once
from app.platform.settings import get_settings
from conftest import assembled_app, migration_config
from fastapi import APIRouter, Depends
from PIL import Image, ImageDraw
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


def create_browser_test_app():
    settings = get_settings()
    url = settings.database_url.get_secret_value()
    if settings.app_mode != "fixture" or make_url(url).database != "egrant_test_documents_e2e":
        raise RuntimeError("Browser tests require the dedicated egrant_test_documents_e2e database")
    engine = create_engine(url, hide_parameters=True)
    with engine.begin() as session:
        session.execute(text("DROP SCHEMA public CASCADE"))
        session.execute(text("CREATE SCHEMA public"))
    command.upgrade(migration_config(), "documents@head")
    factory = sessionmaker(engine, expire_on_commit=False)
    app = assembled_app(factory)
    sample_path = Path(__file__).resolve().parents[2] / ".private/browser-sample.png"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample = Image.new("RGB", (600, 150), "white")
    ImageDraw.Draw(sample).text((30, 50), "Sample OCR document", fill="black", font_size=36)
    sample.save(sample_path)
    fixture_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_access)])
    profile = Profile.model_validate_json(
        (Path(__file__).resolve().parents[2] / "contracts/examples/profile.json").read_text(
            encoding="utf-8"
        )
    )
    extractions = []

    @fixture_router.get("/profiles", response_model=Page[Profile])
    def profiles():
        return {"data": [profile], "pagination": {"limit": 200, "offset": 0, "total": 1}}

    @fixture_router.get("/extractions", response_model=Page[Extraction])
    def list_extractions():
        return {
            "data": extractions,
            "pagination": {"limit": 200, "offset": 0, "total": len(extractions)},
        }

    @fixture_router.post("/extractions", response_model=Success[ExtractionBatch], status_code=202)
    def create_extractions(request: CreateExtractions):
        queued = []
        with factory() as session:
            for document_id in request.document_ids:
                sources = get_normalized(session, document_id)
                assert sources.units
                extraction = Extraction(
                    id=uuid4(),
                    document_id=document_id,
                    profile_id=request.profile_id,
                    profile_version=request.profile_version,
                    status="ready",
                    mode="fixture",
                    fields=[],
                    tables=[],
                    warnings=[],
                    error=None,
                    created_at=datetime.now(UTC),
                )
                extractions.append(extraction)
                queued.append(
                    QueuedExtraction(id=extraction.id, document_id=document_id, status="ready")
                )
        return {"data": {"extractions": queued}}

    @fixture_router.get("/capabilities")
    def capabilities():
        return {
            "data": {
                "ocrConfigured": ocr_configured(),
                "aiConfigured": False,
                "egrantConfigured": False,
                "mode": "fixture",
            }
        }

    app.router.routes[0:0] = fixture_router.routes
    registry = JobRegistry()
    registry.register_handler("document.process", process_document)
    stop = threading.Event()

    def worker():
        while not stop.is_set():
            if not run_once(factory, registry):
                stop.wait(0.1)

    @asynccontextmanager
    async def lifespan(app):
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        yield
        stop.set()
        thread.join(timeout=10)
        engine.dispose()

    app.router.lifespan_context = lifespan
    return app


if __name__ == "__main__":
    uvicorn.run(create_browser_test_app(), host="127.0.0.1", port=8012, access_log=False)
