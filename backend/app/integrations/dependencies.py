"""Resolve only public owner interfaces; never substitute reference fixtures."""

from importlib import import_module
from uuid import UUID

from sqlalchemy.orm import Session

from app.platform.contracts import Extraction, FormDefinition, Profile, Review
from app.platform.errors import UnavailableError


def public_service(module: str, name: str):
    try:
        service = import_module(f"app.{module}.service")
    except ModuleNotFoundError as error:
        if error.name not in {f"app.{module}", f"app.{module}.service"}:
            raise
        raise UnavailableError() from None
    return getattr(service, name)


def get_confirmed_review(session: Session, id: UUID, revision: int) -> Review:
    return public_service("reviews", "get_confirmed_review")(session, id, revision)


def get_extraction(session: Session, id: UUID) -> Extraction:
    return public_service("extraction", "get_extraction")(session, id)


def get_profile(session: Session, id: UUID, version: int) -> Profile:
    return public_service("profiles", "get_profile")(session, id, version)


def get_form(session: Session, id: UUID) -> FormDefinition:
    return public_service("profiles", "get_form")(session, id)
