"""Exercise production router assembly against a disposable migrated database."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from app.main import create_app
from app.platform.settings import get_settings
from sqlalchemy.engine import make_url

url = get_settings().database_url.get_secret_value()
if not (make_url(url).database or "").startswith("egrant_test"):
    raise RuntimeError("Profiles browser tests require an isolated egrant_test database")
root = Path(__file__).resolve().parents[2]
config = Config(str(root / "backend/alembic.ini"))
config.set_main_option("script_location", str(root / "backend/migrations"))
command.upgrade(config, "head")
app = create_app()
