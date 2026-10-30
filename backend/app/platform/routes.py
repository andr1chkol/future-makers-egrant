"""Frozen domain routes are explicit unavailable shells until owners assemble them."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.platform.contracts import (
    ConfirmReview,
    CreateExtractions,
    Extraction,
    ExtractionBatch,
    Page,
    Review,
    SaveReview,
    Success,
)
from app.platform.errors import UnavailableError

router = APIRouter()
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


@router.post("/extractions", status_code=202, response_model=Success[ExtractionBatch])
def create_extractions(request: CreateExtractions):
    raise UnavailableError()


@router.get("/extractions", response_model=Page[Extraction])
def list_extractions(limit: Limit = 50, offset: Offset = 0):
    raise UnavailableError()


@router.get("/extractions/{id}", response_model=Success[Extraction])
def get_extraction(id: UUID):
    raise UnavailableError()


@router.post("/extractions/{id}/retries", status_code=202, response_model=Success[Extraction])
def retry_extraction(id: UUID):
    raise UnavailableError()


@router.get("/reviews/{extraction_id}", response_model=Success[Review])
def get_review(extraction_id: UUID):
    raise UnavailableError()


@router.put("/reviews/{extraction_id}", response_model=Success[Review])
def save_review(extraction_id: UUID, request: SaveReview):
    raise UnavailableError()


@router.post("/reviews/{extraction_id}/confirm", response_model=Success[Review])
def confirm_review(extraction_id: UUID, request: ConfirmReview):
    raise UnavailableError()
