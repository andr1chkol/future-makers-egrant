import subprocess
from collections.abc import Callable

from app.documents.settings import DocumentSettings
from app.platform.errors import DomainError

OCR = Callable[[bytes, float], str]


def ocr_configured(settings: DocumentSettings | None = None) -> bool:
    settings = settings or DocumentSettings()
    executable = settings.ocr_executable
    return bool(
        settings.ocr_provider == "tesseract"
        and executable
        and executable.is_absolute()
        and executable.is_file()
    )


def configured_ocr(settings: DocumentSettings) -> OCR:
    def recognize(image: bytes, remaining_seconds: float) -> str:
        # Only an explicitly selected local adapter is supported. eGrant has no supplied OCR API.
        if not ocr_configured(settings):
            raise DomainError("OCR_UNAVAILABLE", 503, "OCR integration is not configured")
        try:
            result = subprocess.run(
                [
                    str(settings.ocr_executable),
                    "stdin",
                    "stdout",
                    "-l",
                    settings.ocr_languages,
                ],
                input=image,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=max(0.1, min(settings.ocr_seconds, remaining_seconds)),
                check=True,
            )
            return result.stdout.decode("utf-8", errors="strict")
        except subprocess.TimeoutExpired:
            raise DomainError("OCR_TIMEOUT", 502, "OCR exceeded its time limit") from None
        except (OSError, subprocess.CalledProcessError, UnicodeError):
            raise DomainError("OCR_FAILED", 502, "OCR provider failed") from None

    return recognize
