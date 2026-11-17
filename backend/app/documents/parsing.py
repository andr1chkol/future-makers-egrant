import json
import os
import subprocess
import sys
from uuid import UUID

from app.documents.normalization import Normalization
from app.documents.settings import DocumentSettings
from app.platform.contracts import SourceUnit, Warning
from app.platform.errors import DomainError


def parse_document(
    content: bytes,
    media_type: str,
    document_id: UUID,
    *,
    validation_only: bool = False,
) -> Normalization:
    settings = DocumentSettings()
    timeout = settings.validation_seconds if validation_only else settings.processing_seconds
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(sys.path)
    try:
        # Native PDF parsing runs in a separate process: it is not thread safe and must be killable.
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.documents.parse_worker",
                media_type,
                str(document_id),
                "validate" if validation_only else "normalize",
            ],
            input=content,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            env=environment,
            check=True,
        )
        payload = json.loads(process.stdout)
        if "error" in payload:
            error = payload["error"]
            raise DomainError(error["code"], error["status"], error["message"])
        return Normalization(
            units=[SourceUnit.model_validate(unit) for unit in payload["units"]],
            warnings=[Warning.model_validate(warning) for warning in payload["warnings"]],
            page_count=payload["pageCount"],
        )
    except subprocess.TimeoutExpired:
        raise DomainError(
            "PROCESSING_TIMEOUT", 502, "Document parsing exceeded its time limit"
        ) from None
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError):
        raise DomainError("PARSING_FAILED", 422, "Document could not be parsed safely") from None
