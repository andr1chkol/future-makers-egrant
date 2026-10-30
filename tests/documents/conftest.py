import io
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from app.documents.routes import router
from app.documents.settings import DocumentSettings
from app.main import create_app
from app.platform.database import get_session
from app.platform.routes import router as platform_router
from fastapi import APIRouter
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


@pytest.fixture(autouse=True)
def deterministic_document_settings(monkeypatch):
    # Ordinary tests never inherit a developer's live OCR selection or machine-specific limits.
    for field, definition in DocumentSettings.model_fields.items():
        if definition.default is not None:
            monkeypatch.setenv(f"DOCUMENT_{field.upper()}", str(definition.default))
        else:
            monkeypatch.delenv(f"DOCUMENT_{field.upper()}", raising=False)


@pytest.fixture
def document_database(monkeypatch, tmp_path):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url or not (make_url(url).database or "").startswith("egrant_test"):
        pytest.fail("TEST_DATABASE_URL must identify an isolated egrant_test PostgreSQL database")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("FILE_STORAGE_PATH", str(tmp_path / "private"))
    engine = create_engine(url, hide_parameters=True)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    config = migration_config()
    command.upgrade(config, "documents@head")
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def migration_config():
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "backend/alembic.ini"))
    config.set_main_option("script_location", str(root / "backend/migrations"))
    config.set_main_option("path_separator", "os")
    config.set_main_option(
        "version_locations",
        os.pathsep.join(
            [
                str(root / "backend/migrations/versions"),
                str(root / "backend/app/documents/migrations"),
            ]
        ),
    )
    return config


@pytest.fixture
def storage_compatibility(monkeypatch):
    # Shared storage currently requires a POSIX flag. This test-only shim is NOT a runtime fix.
    if not hasattr(os, "O_NOFOLLOW"):
        monkeypatch.setattr(os, "O_NOFOLLOW", 0, raising=False)


def assembled_app(factory):
    domain_router = APIRouter()
    domain_router.routes[:] = [
        route
        for route in platform_router.routes
        if not getattr(route, "path", "").startswith("/documents")
    ]
    domain_router.include_router(router)
    with patch("app.main.router", domain_router):
        app = create_app()

    def sessions():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = sessions
    return app


@pytest.fixture
def client(document_database):
    with TestClient(
        assembled_app(document_database),
        base_url="http://localhost",
        headers={"Origin": "http://localhost:5173"},
    ) as client:
        yield client


@pytest.fixture
def csv_content():
    return "name,amount\nŽiadosť,12.50\n\nDruhý,20.00\n".encode()


@pytest.fixture
def png_content():
    stream = io.BytesIO()
    Image.new("RGB", (120, 80), "white").save(stream, format="PNG")
    return stream.getvalue()


@pytest.fixture
def text_pdf():
    writer = PdfWriter()
    for label in ["First supporting page", "Second supporting page"]:
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): writer._add_object(font)}
                ),
            }
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 14 Tf 20 250 Td ({label}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.fixture
def scanned_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.add_blank_page(width=300, height=300)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
