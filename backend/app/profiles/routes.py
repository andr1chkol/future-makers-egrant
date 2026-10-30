from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.platform.access import require_access
from app.platform.contracts import (
    CreateForm,
    CreateProfileVersion,
    FormDefinition,
    Page,
    Profile,
    ProfileDefinition,
    Success,
)
from app.platform.database import get_session
from app.profiles import service

router = APIRouter(dependencies=[Depends(require_access)])
Database = Annotated[Session, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


@router.post("/forms", status_code=201, response_model=Success[FormDefinition])
def create_form(request: CreateForm, session: Database):
    return {"data": service.create_form(session, request)}


@router.get("/forms", response_model=Page[FormDefinition])
def list_forms(session: Database, limit: Limit = 50, offset: Offset = 0):
    return service.list_forms(session, limit, offset)


@router.get("/forms/{id}", response_model=Success[FormDefinition])
def get_form(id: UUID, session: Database):
    return {"data": service.get_form(session, id)}


@router.post("/profiles", status_code=201, response_model=Success[Profile])
def create_profile(request: ProfileDefinition, session: Database):
    return {"data": service.create_profile(session, request)}


@router.get("/profiles", response_model=Page[Profile])
def list_profiles(session: Database, limit: Limit = 50, offset: Offset = 0):
    return service.list_profiles(session, limit, offset)


@router.get("/profiles/{id}", response_model=Success[Profile])
def get_profile(id: UUID, session: Database, version: Annotated[int | None, Query(ge=1)] = None):
    return {"data": service.get_profile(session, id, version)}


@router.post("/profiles/{id}/versions", status_code=201, response_model=Success[Profile])
def create_version(id: UUID, request: CreateProfileVersion, session: Database):
    return {"data": service.create_version(session, id, request)}
