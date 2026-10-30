"""Frozen domain routes are explicit unavailable shells until owners assemble them."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import Response

from app.platform.contracts import (
    ConfirmReview,
    CreateExtractions,
    Document,
    Extraction,
    ExtractionBatch,
    NormalizedDocument,
    Page,
    Review,
    SaveReview,
    Success,
)
from app.platform.errors import UnavailableError

router = APIRouter()
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


@router.post("/documents", status_code=201, response_model=Success[list[Document]])
def upload_documents(files: Annotated[list[UploadFile], File()]):
    raise UnavailableError()


@router.get("/documents", response_model=Page[Document])
def list_documents(limit: Limit = 50, offset: Offset = 0):
    raise UnavailableError()


@router.get("/documents/{id}", response_model=Success[Document])
def get_document(id: UUID):
    raise UnavailableError()


@router.get(
    "/documents/{id}/content",
    response_class=Response,
    responses={
        200: {
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
            "description": "Private content",
        }
    },
)
def get_content(id: UUID):
    raise UnavailableError()


@router.get("/documents/{id}/normalized", response_model=Success[NormalizedDocument])
def get_normalized(id: UUID):
    raise UnavailableError()


@router.post("/documents/{id}/retries", status_code=202, response_model=Success[Document])
def retry_document(id: UUID):
    raise UnavailableError()


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
