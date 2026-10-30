"""Opt-in OCR smoke check using a permitted local sample, without logging recognized content."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from app.documents.normalization import declared_media_type
from app.documents.ocr import ocr_configured
from app.documents.parsing import parse_document
from app.platform.errors import DomainError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--media-type", required=True)
    arguments = parser.parse_args()
    if not ocr_configured():
        print(json.dumps({"status": "NOT_VERIFIED", "errorCode": "OCR_UNAVAILABLE"}))
        return 2
    document_id = uuid4()
    try:
        content = arguments.sample.read_bytes()
        media_type = declared_media_type(arguments.sample.name, arguments.media_type, content)
        result = parse_document(content, media_type, document_id)
    except DomainError as error:
        print(json.dumps({"status": "FAILED", "errorCode": error.code}))
        return 1
    print(
        json.dumps(
            {
                "status": "PASSED",
                "documentId": str(document_id),
                "unitCount": len(result.units),
                "pageCount": result.page_count,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
