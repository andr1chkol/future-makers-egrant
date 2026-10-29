"""Frozen domain routes are explicit unavailable shells until owners assemble them."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Header, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from app.platform.contracts import (
    ConfirmReview,
    CreateExtractions,
    CreateForm,
    CreateProfileVersion,
    CreateSubmission,
    Document,
    Extraction,
    ExtractionBatch,
    FormDefinition,
    NormalizedDocument,
    Page,
    Profile,
    ProfileDefinition,
    Review,
    SaveReview,
    Submission,
    SubmissionPayload,
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


@router.post("/forms", status_code=201, response_model=Success[FormDefinition])
def create_form(request: CreateForm):
    raise UnavailableError()


@router.get("/forms", response_model=Page[FormDefinition])
def list_forms(limit: Limit = 50, offset: Offset = 0):
    raise UnavailableError()


@router.get("/forms/{id}", response_model=Success[FormDefinition])
def get_form(id: UUID):
    raise UnavailableError()


@router.post("/profiles", status_code=201, response_model=Success[Profile])
def create_profile(request: ProfileDefinition):
    raise UnavailableError()


@router.get("/profiles", response_model=Page[Profile])
def list_profiles(limit: Limit = 50, offset: Offset = 0):
    raise UnavailableError()


@router.get("/profiles/{id}", response_model=Success[Profile])
def get_profile(id: UUID, version: Annotated[int | None, Query(ge=1)] = None):
    raise UnavailableError()


@router.post("/profiles/{id}/versions", status_code=201, response_model=Success[Profile])
def create_version(id: UUID, request: CreateProfileVersion):
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


@router.post(
    "/submissions",
    status_code=201,
    response_model=Success[Submission],
    responses={202: {"model": Success[Submission], "description": "eGrant apply queued"}},
)
def create_submission(
    request: CreateSubmission, idempotency_key: Annotated[str, Header(min_length=1, max_length=128)]
):
    raise UnavailableError()


@router.get("/submissions/{id}", response_model=Success[Submission])
def get_submission(id: UUID):
    raise UnavailableError()


@router.get(
    "/submissions/{id}/export",
    response_class=JSONResponse,
    response_model=SubmissionPayload,
    responses={
        200: {
            "description": "JSON attachment",
            "headers": {"Content-Disposition": {"schema": {"type": "string"}}},
        }
    },
)
def export_submission(id: UUID):
    raise UnavailableError()
