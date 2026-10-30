from copy import deepcopy
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.platform.contracts import (
    CreateForm,
    CreateProfileVersion,
    FormDefinition,
    Page,
    Pagination,
    Profile,
    ProfileDefinition,
)
from app.platform.errors import ConflictError, NotFoundError
from app.platform.logging import log
from app.profiles.importer import normalize_form
from app.profiles.models import ImportedForm, ProfileHead, ProfileVersion
from app.profiles.validation import validate_profile


def get_form(session: Session, id: UUID) -> FormDefinition:
    """Read a detached DTO without committing the caller's transaction."""
    record = session.get(ImportedForm, id)
    if record is None:
        raise NotFoundError()
    # Unknown nested JSON stays detached from SQLAlchemy's session identity map.
    return FormDefinition.model_validate(deepcopy(record.snapshot))


def get_profile(session: Session, id: UUID, version: int | None = None) -> Profile:
    """Resolve a pinned snapshot; historical reads never follow the mutable latest pointer."""
    query = select(ProfileVersion).where(ProfileVersion.profile_id == id)
    if version is None:
        query = query.order_by(ProfileVersion.version.desc()).limit(1)
    else:
        query = query.where(ProfileVersion.version == version)
    record = session.scalar(query)
    if record is None:
        raise NotFoundError()
    return Profile.model_validate(record.snapshot)


def create_form(session: Session, request: CreateForm) -> FormDefinition:
    form = normalize_form(request.name, request.definition)
    with session.begin():
        session.add(
            ImportedForm(
                id=form.id, name=form.name, snapshot=form.model_dump(mode="json", by_alias=True)
            )
        )
    return form


def create_profile(session: Session, request: ProfileDefinition) -> Profile:
    with session.begin():
        form = get_form(session, request.form_id)
        validate_profile(request, form)
        profile = Profile(id=uuid4(), version=1, **request.model_dump())
        session.add(ProfileHead(id=profile.id, latest_version=1))
        session.flush()
        session.add(
            ProfileVersion(
                profile_id=profile.id,
                version=profile.version,
                form_id=profile.form_id,
                snapshot=profile.model_dump(mode="json", by_alias=True),
            )
        )
    log("profile.created", profileId=profile.id, formId=profile.form_id, version=profile.version)
    return profile


def create_version(session: Session, id: UUID, request: CreateProfileVersion) -> Profile:
    with session.begin():
        # Serialize version allocation so two saves of the same expected version cannot win.
        head = session.scalar(select(ProfileHead).where(ProfileHead.id == id).with_for_update())
        if head is None:
            raise NotFoundError()
        if head.latest_version != request.expected_version:
            raise ConflictError()
        form = get_form(session, request.form_id)
        validate_profile(request, form)
        profile = Profile(
            id=id,
            version=head.latest_version + 1,
            **request.model_dump(exclude={"expected_version"}),
        )
        head.latest_version = profile.version
        # Append a new row. PostgreSQL triggers also reject direct snapshot updates or deletes.
        session.add(
            ProfileVersion(
                profile_id=id,
                version=profile.version,
                form_id=profile.form_id,
                snapshot=profile.model_dump(mode="json", by_alias=True),
            )
        )
    log("profile.version_created", profileId=id, formId=profile.form_id, version=profile.version)
    return profile


def list_forms(session: Session, limit: int = 50, offset: int = 0) -> Page[FormDefinition]:
    total = session.scalar(select(func.count()).select_from(ImportedForm))
    records = session.scalars(
        select(ImportedForm)
        .order_by(ImportedForm.name, ImportedForm.id)
        .limit(limit)
        .offset(offset)
    )
    return Page(
        data=[FormDefinition.model_validate(deepcopy(record.snapshot)) for record in records],
        pagination=Pagination(limit=limit, offset=offset, total=total),
    )


def list_profiles(session: Session, limit: int = 50, offset: int = 0) -> Page[Profile]:
    total = session.scalar(select(func.count()).select_from(ProfileHead))
    query = (
        select(ProfileVersion)
        .join(ProfileHead, ProfileVersion.profile_id == ProfileHead.id)
        .where(ProfileVersion.version == ProfileHead.latest_version)
        .order_by(ProfileVersion.profile_id)
        .limit(limit)
        .offset(offset)
    )
    return Page(
        data=[Profile.model_validate(record.snapshot) for record in session.scalars(query)],
        pagination=Pagination(limit=limit, offset=offset, total=total),
    )
