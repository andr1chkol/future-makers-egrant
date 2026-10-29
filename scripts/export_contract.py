"""Generate committed OpenAPI without environment secrets or database connections."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import yaml
from app.main import create_app

root = Path(__file__).resolve().parents[1]
(root / "contracts/api.yaml").write_text(
    yaml.safe_dump(create_app().openapi(), sort_keys=False, allow_unicode=True)
)
