"""Allowlisted operational data; arbitrary messages and exception text never reach stdout."""

import json
import logging
import re
import sys
import traceback
from contextvars import ContextVar
from datetime import UTC, datetime
from uuid import UUID

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
job_id: ContextVar[str | None] = ContextVar("job_id", default=None)
job_attempt: ContextVar[int | None] = ContextVar("job_attempt", default=None)
EVENTS = {
    "document.uploaded",
    "document.processing_started",
    "document.ready",
    "document.failed",
    "document.duplicate_detected",
    "extraction.started",
    "extraction.validation_warning",
    "extraction.ready",
    "extraction.failed",
    "profile.created",
    "profile.version_created",
    "review.saved",
    "review.conflict",
    "review.confirmed",
    "submission.prepared",
    "submission.applied",
    "submission.unknown",
    "submission.failed",
    "job.retry_scheduled",
    "job.completed",
    "job.failed",
    "worker.started",
    "request.completed",
    "request.failed",
}
ID_KEYS = {
    "requestId",
    "jobId",
    "documentId",
    "extractionId",
    "submissionId",
    "profileId",
    "formId",
}
NUMBER_KEYS = {"durationMs", "attempt", "revision", "version"}


def safe_id(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return "[REDACTED]"


class JsonFormatter(logging.Formatter):
    def format(self, record):
        event = getattr(record, "event", "request.failed")
        if event not in EVENTS:
            event = "request.failed"
        result = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": event,
            "message": event,
        }
        context = dict(getattr(record, "context", {}))
        if request_id.get():
            context.setdefault("requestId", request_id.get())
        if job_id.get():
            context.setdefault("jobId", job_id.get())
        if job_attempt.get() is not None:
            context.setdefault("attempt", job_attempt.get())
        for key, value in context.items():
            if key in ID_KEYS:
                result[key] = safe_id(value)
            elif (
                key in NUMBER_KEYS
                and isinstance(value, (float, int))
                and not isinstance(value, bool)
            ):
                result[key] = value
            elif key == "errorCode":
                result[key] = value if re.fullmatch(r"[A-Z_]{1,64}", str(value)) else "[REDACTED]"
        if record.exc_info:
            # File basenames and line numbers locate failures without serializing source or locals.
            result["stack"] = [
                {"file": frame.filename.rsplit("/", 1)[-1], "line": frame.lineno}
                for frame in traceback.extract_tb(record.exc_info[2])
            ]
        return json.dumps(result)


logger = logging.getLogger("egrant")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)


def log(event: str, *, level: int = logging.INFO, exc_info=False, **context):
    logger.log(level, event, extra={"event": event, "context": context}, exc_info=exc_info)
