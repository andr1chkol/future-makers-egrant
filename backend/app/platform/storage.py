import os
from pathlib import Path
from uuid import UUID, uuid4

from app.platform.errors import DomainError, NotFoundError


class PrivateStorage:
    def __init__(self, root: Path):
        if os.name != "posix" or not hasattr(os, "O_NOFOLLOW"):
            raise DomainError(
                "STORAGE_UNAVAILABLE",
                503,
                "Private storage requires a POSIX runtime; use the Linux containers",
            )
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def put(self, document_id: UUID, content: bytes) -> None:
        if len(content) > 20 * 1024 * 1024:
            raise DomainError("UPLOAD_TOO_LARGE", 413, "File exceeds 20 MiB")
        target = self.root / str(UUID(str(document_id)))
        temporary = self.root / f".{uuid4()}"
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            # A hard link installs atomically without replacing an existing immutable document.
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def read(self, document_id: UUID) -> bytes:
        target = self.root / str(UUID(str(document_id)))
        try:
            descriptor = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, "rb") as stream:
                return stream.read()
        except FileNotFoundError:
            raise NotFoundError() from None
