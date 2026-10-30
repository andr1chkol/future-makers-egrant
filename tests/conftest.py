import os
import subprocess
import sys

import pytest
from app.platform.database import session_factory
from app.platform.settings import get_settings
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


@pytest.fixture(autouse=True)
def fixture_settings(monkeypatch):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("APP_MODE", "fixture")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://localhost:5173")
    get_settings.cache_clear()
    session_factory.cache_clear()
    yield
    get_settings.cache_clear()
    session_factory.cache_clear()


def validate_test_database_url(url):
    parsed = make_url(url)
    # Driver query parameters can override the database named in the URL path.
    if (
        parsed.get_backend_name() != "postgresql"
        or parsed.query
        or not (parsed.database or "").startswith("egrant_test")
    ):
        raise ValueError(
            "An isolated PostgreSQL egrant_test database without URL query is required"
        )


@pytest.fixture
def database(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("TEST_DATABASE_URL must point to an isolated PostgreSQL database")
    try:
        validate_test_database_url(url)
    except ValueError as error:
        pytest.fail(str(error))
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    engine = create_engine(url, hide_parameters=True)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        check=True,
    )
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()
