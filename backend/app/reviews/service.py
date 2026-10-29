import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.platform.contracts import (
    ConfirmReview,
    Extraction,
    FormDefinition,
    Profile,
    Review,
    ReviewSnapshot,
    SaveReview,
)
from app.platform.errors import ConflictError, NotFoundError
from app.platform.logging import log
from app.reviews.context import load_context
from app.reviews.models import ReviewRecord, ReviewRevision
from app.reviews.validation import validate_snapshot


def as_review(record: ReviewRecord) -> Review:
    return Review(
        extraction_id=record.extraction_id,
        revision=record.revision,
        status=record.status,
        confirmed_at=record.confirmed_at,
        **record.snapshot,
    )


def remember_revision(session: Session, record: ReviewRecord) -> None:
    session.add(
        ReviewRevision(
            extraction_id=record.extraction_id,
            revision=record.revision,
            status=record.status,
            snapshot=record.snapshot,
            confirmed_at=record.confirmed_at,
        )
    )


def get_review(session: Session, extraction_id: UUID) -> Review:
    """Lazily initialize once from a ready extraction using a fresh Session."""
    with session.begin():
        record = session.get(ReviewRecord, extraction_id)
        if record is None:
            extraction, profile, form = load_context(session, extraction_id)
            if extraction.id != extraction_id or extraction.status != "ready":
                raise ConflictError()
            snapshot = ReviewSnapshot(
                fields=[{"key": field.key, "value": field.value} for field in extraction.fields],
                tables=[
                    {
                        "key": table.key,
                        "rows": [
                            {
                                "rowId": row.row_id,
                                "cells": [
                                    {"key": cell.key, "value": cell.value} for cell in row.cells
                                ],
                            }
                            for row in table.rows
                        ],
                    }
                    for table in extraction.tables
                ],
                acknowledged_warnings=[],
            )
            validate_snapshot(snapshot, extraction, profile, form)
            # Concurrent first reads converge on one draft instead of resetting a winner.
            created = session.scalar(
                insert(ReviewRecord)
                .values(
                    extraction_id=extraction_id,
                    revision=0,
                    status="draft",
                    confirmed_at=None,
                    snapshot=snapshot.model_dump(mode="json", by_alias=True),
                    extraction_snapshot=extraction.model_dump(mode="json", by_alias=True),
                    profile_snapshot=profile.model_dump(mode="json", by_alias=True),
                    form_snapshot=form.model_dump(mode="json", by_alias=True),
                )
                .on_conflict_do_nothing(index_elements=[ReviewRecord.extraction_id])
                .returning(ReviewRecord.extraction_id)
            )
            record = session.get(ReviewRecord, extraction_id)
            if created:
                remember_revision(session, record)
        result = as_review(record)
    return result


def locked_review(session: Session, extraction_id: UUID, revision: int) -> ReviewRecord:
    record = session.scalar(
        select(ReviewRecord)
        .where(ReviewRecord.extraction_id == extraction_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if record is None:
        raise NotFoundError()
    if record.revision != revision:
        log(
            "review.conflict",
            level=logging.WARNING,
            extractionId=extraction_id,
            revision=record.revision,
            errorCode="STALE_REVIEW",
        )
        raise ConflictError()
    return record


def save_review(session: Session, extraction_id: UUID, request: SaveReview) -> Review:
    """Replace the full draft atomically; confirmed revisions cannot be edited."""
    with session.begin():
        record = locked_review(session, extraction_id, request.expected_revision)
        if record.status == "confirmed":
            log(
                "review.conflict",
                level=logging.WARNING,
                extractionId=extraction_id,
                revision=record.revision,
                errorCode="REVIEW_IMMUTABLE",
            )
            raise ConflictError()
        snapshot = ReviewSnapshot.model_validate(request.model_dump(exclude={"expected_revision"}))
        validate_snapshot(
            snapshot,
            Extraction.model_validate(record.extraction_snapshot),
            Profile.model_validate(record.profile_snapshot),
            FormDefinition.model_validate(record.form_snapshot),
        )
        record.snapshot = snapshot.model_dump(mode="json", by_alias=True)
        record.revision += 1
        remember_revision(session, record)
        result = as_review(record)
    log("review.saved", extractionId=extraction_id, revision=result.revision)
    return result


def confirm_review(session: Session, extraction_id: UUID, request: ConfirmReview) -> Review:
    """Confirm the saved revision, or return its already-confirmed current result."""
    with session.begin():
        record = locked_review(session, extraction_id, request.expected_revision)
        if record.status == "confirmed":
            return as_review(record)
        snapshot = ReviewSnapshot.model_validate(record.snapshot)
        validate_snapshot(
            snapshot,
            Extraction.model_validate(record.extraction_snapshot),
            Profile.model_validate(record.profile_snapshot),
            FormDefinition.model_validate(record.form_snapshot),
            confirming=True,
        )
        record.revision += 1
        record.status = "confirmed"
        record.confirmed_at = datetime.now(UTC)
        remember_revision(session, record)
        result = as_review(record)
    log("review.confirmed", extractionId=extraction_id, revision=result.revision)
    return result


def get_confirmed_review(session: Session, id: UUID, revision: int) -> Review:
    """Read the exact immutable confirmed revision; never commit the caller's transaction."""
    record = session.get(ReviewRecord, id, populate_existing=True)
    if record is None:
        raise NotFoundError()
    if record.status != "confirmed" or record.revision != revision:
        raise ConflictError()
    return as_review(record)
