import copy
import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from app.platform.contracts import CreateForm, CreateProfileVersion, ProfileDefinition
from app.platform.errors import ConflictError, DomainError, NotFoundError
from app.platform.logging import JsonFormatter, logger, request_id
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def create_examples(database, form_payload, profile_payload):
    from app.profiles.service import create_form, create_profile

    with database() as session:
        form = create_form(session, CreateForm.model_validate(form_payload))
    profile_payload["formId"] = str(form.id)
    with database() as session:
        profile = create_profile(session, ProfileDefinition.model_validate(profile_payload))
    return form, profile


def test_versions_are_durable_immutable_and_public_reads_do_not_commit(
    profiles_database,
    form_payload,
    profile_payload,
):
    from app.profiles.service import create_version, get_form, get_profile

    database = profiles_database
    form, profile = create_examples(database, form_payload, profile_payload)
    snapshot = profile.model_dump(mode="json", by_alias=True)
    with database() as session:
        newer = create_version(
            session,
            profile.id,
            CreateProfileVersion(expected_version=1, **{**profile_payload, "name": "Edited label"}),
        )
    assert newer.version == 2
    with database() as session:
        assert (
            get_profile(session, profile.id, 1).model_dump(mode="json", by_alias=True) == snapshot
        )
        assert get_profile(session, profile.id).version == 2
        assert get_form(session, form.id).original_json == form_payload["definition"]
        assert session.in_transaction()
        session.rollback()
    # The exact extraction-pinned ID/version resolves the old mapping after later edits.
    extraction_reference = {"profileId": profile.id, "profileVersion": 1}
    with database() as session:
        pinned = get_profile(
            session, extraction_reference["profileId"], extraction_reference["profileVersion"]
        )
        pinned.scalar_fields[0].label = "Mutated client DTO"
    with database() as session:
        assert (
            get_profile(session, profile.id, 1).scalar_fields[0].label
            == profile.scalar_fields[0].label
        )
    for statement in [
        "UPDATE profile_versions SET snapshot = '{}'::jsonb",
        "DELETE FROM profile_versions",
        "UPDATE profile_forms SET name = 'changed'",
        "DELETE FROM profile_forms",
    ]:
        with database.begin() as session, pytest.raises(IntegrityError):
            session.execute(text(statement))


def test_concurrent_saves_create_exactly_one_version(
    profiles_database, form_payload, profile_payload
):
    from app.profiles.service import create_version, get_profile

    database = profiles_database
    _, profile = create_examples(database, form_payload, profile_payload)
    barrier = Barrier(2)

    def save(name):
        request = CreateProfileVersion.model_validate(
            {**profile_payload, "name": name, "expectedVersion": 1}
        )
        barrier.wait(timeout=10)
        try:
            with database() as session:
                return create_version(session, profile.id, request).version
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(save, ["First", "Second"]))
    assert sorted(outcomes, key=str) == [2, "conflict"]
    with database() as session:
        assert get_profile(session, profile.id).version == 2
        with pytest.raises(NotFoundError):
            get_profile(session, profile.id, 3)


def test_invalid_version_rolls_back_latest_pointer(
    profiles_database, form_payload, profile_payload
):
    from app.profiles.service import create_version, get_profile

    database = profiles_database
    _, profile = create_examples(database, form_payload, profile_payload)
    broken = copy.deepcopy(profile_payload)
    broken["scalarFields"][0]["targetTag"] = "does_not_exist"
    with database() as session, pytest.raises(DomainError):
        create_version(session, profile.id, CreateProfileVersion(expected_version=1, **broken))
    with database() as session:
        assert get_profile(session, profile.id).version == 1
    with database() as session:
        assert (
            create_version(
                session, profile.id, CreateProfileVersion(expected_version=1, **profile_payload)
            ).version
            == 2
        )


def test_missing_resources_use_exact_public_errors(profiles_database):
    from app.profiles.service import get_form, get_profile

    with profiles_database() as session:
        for call in [
            lambda: get_form(session, uuid4()),
            lambda: get_profile(session, uuid4()),
            lambda: get_profile(session, uuid4(), 1),
        ]:
            with pytest.raises(NotFoundError):
                call()


def test_profile_events_emit_safe_context_and_request_correlation(
    profiles_database,
    form_payload,
    profile_payload,
):
    from app.profiles.service import create_version

    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = Capture()
    stream = io.StringIO()
    stdout = logging.StreamHandler(stream)
    stdout.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.addHandler(stdout)
    correlation = str(uuid4())
    token = request_id.set(correlation)
    profile_payload["name"] = "Private name SK123"
    profile_payload["scalarFields"][0]["description"] = "Private account 1234.00"
    try:
        form, profile = create_examples(profiles_database, form_payload, profile_payload)
        with profiles_database() as session:
            create_version(
                session, profile.id, CreateProfileVersion(expected_version=1, **profile_payload)
            )
    finally:
        request_id.reset(token)
        logger.removeHandler(handler)
        logger.removeHandler(stdout)
    assert [record.event for record in records] == ["profile.created", "profile.version_created"]
    assert [record.context["version"] for record in records] == [1, 2]
    assert all(record.context["profileId"] == profile.id for record in records)
    assert all(record.context["formId"] == form.id for record in records)
    lines = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert all(line["requestId"] == correlation and line["level"] == "INFO" for line in lines)
    assert "Private" not in stream.getvalue() and "SK123" not in stream.getvalue()
    assert "1234.00" not in stream.getvalue()


def test_module_migration_can_downgrade_and_reapply(profiles_database):
    from alembic import command
    from alembic.config import Config

    config = Config("backend/app/profiles/alembic.ini")
    command.downgrade(config, "0001_platform")
    command.upgrade(config, "head")
    with profiles_database() as session:
        assert session.scalar(text("SELECT count(*) FROM profile_versions")) == 0
