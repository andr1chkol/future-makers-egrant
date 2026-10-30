"""Remove old unaccepted originals without racing active intake transactions."""

import time
from uuid import UUID

from sqlalchemy import func, select

from app.documents.models import StoredDocument
from app.documents.service import storage
from app.platform.database import session_factory


def cleanup_orphans(factory, *, minimum_age_seconds=3600) -> int:
    if minimum_age_seconds < 3600:
        raise ValueError("Orphan cleanup requires at least one hour of grace")
    removed = 0
    for path in storage().root.iterdir():
        try:
            document_id = UUID(path.name)
        except ValueError:
            continue
        if path.is_symlink() or not path.is_file():
            continue
        if time.time() - path.stat().st_mtime < minimum_age_seconds:
            continue
        with factory.begin() as session:
            locked = session.scalar(
                select(func.pg_try_advisory_xact_lock(-1 - (document_id.int % (2**63 - 1))))
            )
            if not locked or session.get(StoredDocument, document_id) is not None:
                continue
            path.unlink(missing_ok=True)
            removed += 1
    return removed


if __name__ == "__main__":
    cleanup_orphans(session_factory())
