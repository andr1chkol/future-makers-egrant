"""Public module reads only; no fixture fallback or access to neighboring tables."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.platform.contracts import Extraction, FormDefinition, Profile
from app.platform.errors import UnavailableError


def load_context(
    session: Session, extraction_id: UUID
) -> tuple[Extraction, Profile, FormDefinition]:
    try:
        from app.extraction.service import get_extraction
        from app.profiles.service import get_form, get_profile
    except ModuleNotFoundError as error:
        if error.name in {
            "app.extraction",
            "app.extraction.service",
            "app.profiles",
            "app.profiles.service",
        }:
            raise UnavailableError() from None
        raise
    extraction = get_extraction(session, extraction_id)
    profile = get_profile(session, extraction.profile_id, extraction.profile_version)
    form = get_form(session, profile.form_id)
    return extraction, profile, form
