"""Run the production API and worker against the dedicated fixture acceptance database."""

import os
import signal
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
url = os.environ["FULL_PRODUCT_E2E_DATABASE_URL"]
parsed_url = make_url(url)
if (
    parsed_url.get_backend_name() != "postgresql"
    or parsed_url.query
    or parsed_url.database != "egrant_test_full_product_e2e"
):
    raise RuntimeError(
        "Dedicated PostgreSQL acceptance database URL without query parameters required"
    )
os.chdir(ROOT)
os.environ.update(
    DATABASE_URL=url,
    APP_MODE="fixture",
    DEV_AUTH_BYPASS="true",
    COOKIE_SECURE="false",
    PUBLIC_ORIGIN="http://localhost:5179",
    PYTHONPATH=str(ROOT / "backend"),
)
engine = create_engine(url, hide_parameters=True)
with engine.begin() as connection:
    connection.execute(text("DROP SCHEMA public CASCADE"))
    connection.execute(text("CREATE SCHEMA public"))
engine.dispose()
subprocess.run(
    [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
    check=True,
)
with TemporaryDirectory(prefix="egrant-full-product-") as storage:
    os.environ["FILE_STORAGE_PATH"] = storage
    worker = subprocess.Popen([sys.executable, "-m", "app.worker"])
    api = None

    def stop(signum, frame):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        api = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8017",
                "--no-access-log",
            ]
        )
        raise SystemExit(api.wait())
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        for process in (api, worker):
            if process is None:
                continue
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
