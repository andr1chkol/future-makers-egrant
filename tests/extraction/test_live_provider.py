"""Paid call to the configured OpenAI model with a synthetic document.

Disabled in ordinary checks. Enable explicitly, with permitted credentials:

    export EXTRACTION_LIVE_TEST=1 OPENAI_API_KEY=... OPENAI_MODEL=...
    uv run pytest tests/extraction/test_live_provider.py
"""

import os

import pytest
from app.extraction.assembly import assemble_extraction
from app.extraction.providers import OpenAIProvider
from app.extraction.schema import parse_provider_output
from app.platform.settings import Settings
from extraction_support import example_document, example_profile

pytestmark = pytest.mark.skipif(
    os.environ.get("EXTRACTION_LIVE_TEST") != "1", reason="live provider test not enabled"
)


def test_live_extraction_of_synthetic_invoice():
    provider = OpenAIProvider.from_settings(Settings(_env_file=None))
    assert provider is not None, "OPENAI_API_KEY and OPENAI_MODEL are required"
    profile, document = example_profile(), example_document()
    raw = parse_provider_output(provider.extract(profile, {}, document), profile)
    result = assemble_extraction(raw, profile, document, {})
    fields = {field.key: field.model_dump(mode="json")["value"] for field in result.fields}
    assert fields["supplier"] == "Demo Paper s.r.o."
    assert fields["buyer"] == "Demo Grant Association"
    assert fields["total"] == {"amount": "55.00", "currency": "EUR"}
    assert fields["purchase_order"] is None
    assert len(result.tables[0].rows) == 2
