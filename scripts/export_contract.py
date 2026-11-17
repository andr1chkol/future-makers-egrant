"""Generate committed OpenAPI without environment secrets or database connections."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import yaml
from app.main import create_app

root = Path(__file__).resolve().parents[1]
schema = create_app().openapi()
contract = root / "contracts/api.yaml"
# Router registration can change mapping order without changing the wire contract.
if not contract.exists() or yaml.safe_load(contract.read_text()) != schema:
    contract.write_text(yaml.safe_dump(schema, sort_keys=False, allow_unicode=True))
