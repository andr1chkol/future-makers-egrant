import io
import json
import logging
from uuid import UUID

import pytest
from app.extraction import service
from app.platform.contracts import FormDefinition, NormalizedDocument, Profile
from app.platform.errors import ConflictError, NotFoundError
from app.platform.logging import JsonFormatter, logger
from extraction_support import example_document, example_form, example_profile


@pytest.fixture
def modules(monkeypatch):
    """Stand-ins for the documents and profiles modules' public functions."""

    class Registry:
        def __init__(self):
            self.profiles = {(example_profile().id, 1): example_profile()}
            self.forms = {example_form().id: example_form()}
            self.documents = {example_document().document_id: example_document()}
            self.not_ready: set[UUID] = set()

        def add_document(self, document: NormalizedDocument):
            self.documents[document.document_id] = document

        def add_profile(self, profile: Profile, form: FormDefinition | None = None):
            self.profiles[(profile.id, profile.version)] = profile
            if form:
                self.forms[form.id] = form

    registry = Registry()

    def load_normalized(session, document_id):
        if document_id in registry.not_ready:
            raise ConflictError()
        if document_id not in registry.documents:
            raise NotFoundError()
        return registry.documents[document_id]

    def load_profile(session, profile_id, version):
        if (profile_id, version) not in registry.profiles:
            raise NotFoundError()
        return registry.profiles[(profile_id, version)]

    def load_form(session, form_id):
        if form_id not in registry.forms:
            raise NotFoundError()
        return registry.forms[form_id]

    monkeypatch.setattr(service, "load_normalized", load_normalized)
    monkeypatch.setattr(service, "load_profile", load_profile)
    monkeypatch.setattr(service, "load_form", load_form)
    return registry


@pytest.fixture
def captured_logs():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    def records():
        return [json.loads(line) for line in stream.getvalue().splitlines()]

    records.text = stream.getvalue
    yield records
    logger.removeHandler(handler)
