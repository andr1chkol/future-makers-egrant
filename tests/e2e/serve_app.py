"""Start the production application against an explicitly isolated browser database."""

import os
import sys
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "backend"))
url = os.environ["DATABASE_URL"]
if not (make_url(url).database or "").startswith("egrant_test"):
    raise RuntimeError("Browser tests require an isolated egrant_test database")
os.chdir(root)
command.upgrade(Config(str(root / "backend/alembic.ini")), "head")
uvicorn.run("app.main:app", host="127.0.0.1", port=8011, access_log=False)
