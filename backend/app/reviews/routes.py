from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.platform.access import require_access
from app.platform.contracts import ConfirmReview, Review, SaveReview, Success
from app.platform.database import get_session
from app.reviews import service

router = APIRouter(dependencies=[Depends(require_access)])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get("/reviews/{extraction_id}", response_model=Success[Review])
def get_review(extraction_id: UUID, session: DatabaseSession):
    return {"data": service.get_review(session, extraction_id)}


@router.put("/reviews/{extraction_id}", response_model=Success[Review])
def save_review(extraction_id: UUID, request: SaveReview, session: DatabaseSession):
    return {"data": service.save_review(session, extraction_id, request)}


@router.post("/reviews/{extraction_id}/confirm", response_model=Success[Review])
def confirm_review(extraction_id: UUID, request: ConfirmReview, session: DatabaseSession):
    return {"data": service.confirm_review(session, extraction_id, request)}
