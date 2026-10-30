"""Private pipe protocol. Never print parser diagnostics or document content to logs."""

import json
import logging
import os
import sys
import warnings
from uuid import UUID

from app.documents.normalization import normalize
from app.documents.settings import DocumentSettings
from app.platform.errors import DomainError


def main():
    logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore")
    # Deployment uses Linux; address-space limits complement byte/pixel/archive limits.
    if sys.platform != "win32":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    settings = DocumentSettings()
    try:
        content = sys.stdin.buffer.read(settings.max_bytes + 1)
        result = normalize(
            content,
            sys.argv[1],
            UUID(sys.argv[2]),
            settings,
            validation_only=sys.argv[3] == "validate",
        )
        payload = {
            "units": [unit.model_dump(mode="json", by_alias=True) for unit in result.units],
            "warnings": [
                warning.model_dump(mode="json", by_alias=True) for warning in result.warnings
            ],
            "pageCount": result.page_count,
        }
    except DomainError as error:
        payload = {"error": {"code": error.code, "status": error.status, "message": error.message}}
    except ImportError:
        payload = {
            "error": {
                "code": "DOCUMENT_DEPENDENCY_UNAVAILABLE",
                "status": 503,
                "message": "Document format dependencies are not installed",
            }
        }
    except Exception:
        payload = {
            "error": {
                "code": "CORRUPT_FILE",
                "status": 422,
                "message": "Document is corrupt or unsupported",
            }
        }
    sys.stdout.write(json.dumps(payload, ensure_ascii=True))


if __name__ == "__main__":
    with open(os.devnull, "w") as diagnostics:
        sys.stderr = diagnostics
        main()
