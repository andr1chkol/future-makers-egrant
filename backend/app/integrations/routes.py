from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.integrations import service
from app.platform.contracts import CreateSubmission, Submission, SubmissionPayload, Success
from app.platform.database import get_session

router = APIRouter()
Database = Annotated[Session, Depends(get_session)]


@router.post(
    "/submissions",
    status_code=201,
    response_model=Success[Submission],
    responses={202: {"model": Success[Submission], "description": "eGrant apply queued"}},
)
def create_submission(
    request: CreateSubmission,
    session: Database,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
):
    return {"data": service.create_submission(session, request, idempotency_key)}


@router.get("/submissions/{id}", response_model=Success[Submission])
def get_submission(id: UUID, session: Database):
    return {"data": service.get_submission(session, id)}


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
def export_submission(id: UUID, session: Database):
    payload = service.export_submission(session, id)
    return JSONResponse(
        content=payload.model_dump(mode="json", by_alias=True),
        headers={"Content-Disposition": f'attachment; filename="submission-{id}.json"'},
    )
