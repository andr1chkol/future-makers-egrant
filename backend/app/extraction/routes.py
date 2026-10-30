"""Extraction routes, relative to /api/v1. Member 5 mounts this router behind require_access."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.extraction import service
from app.platform.contracts import CreateExtractions, Extraction, ExtractionBatch, Page, Success
from app.platform.database import get_session

router = APIRouter()
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.post("/extractions", status_code=202, response_model=Success[ExtractionBatch])
def create_extractions(request: CreateExtractions, session: DatabaseSession):
    return {"data": service.create_extractions(session, request)}


@router.get("/extractions", response_model=Page[Extraction])
def list_extractions(session: DatabaseSession, limit: Limit = 50, offset: Offset = 0):
    extractions, total = service.list_extractions(session, limit, offset)
    return {"data": extractions, "pagination": {"limit": limit, "offset": offset, "total": total}}


@router.get("/extractions/{id}", response_model=Success[Extraction])
def get_extraction(id: UUID, session: DatabaseSession):
    return {"data": service.get_extraction(session, id)}


@router.post("/extractions/{id}/retries", status_code=202, response_model=Success[Extraction])
def retry_extraction(id: UUID, session: DatabaseSession):
    return {"data": service.retry_extraction(session, id)}
