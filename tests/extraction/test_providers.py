import io
import json
from urllib.error import HTTPError, URLError

import pytest
from app.extraction import providers
from app.extraction.providers import (
    FixtureProvider,
    OpenAIProvider,
    ProviderError,
    fixture_fingerprint,
)
from app.platform.contracts import NormalizedDocument
from extraction_support import example_document, example_profile, reply_for

SECRET = "sk-test-not-a-real-key-0000"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def completed(text: str) -> dict:
    return {
        "status": "completed",
        "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [{"type": "output_text", "text": text}]},
        ],
    }


@pytest.fixture
def calls(monkeypatch):
    recorded = []

    def install(outcome):
        def fake_urlopen(request, timeout):
            recorded.append((request, timeout))
            if isinstance(outcome, Exception):
                raise outcome
            return FakeResponse(json.dumps(outcome).encode())

        monkeypatch.setattr(providers, "urlopen", fake_urlopen)
        return recorded

    return install


def provider():
    return OpenAIProvider(api_key=SECRET, model="test-model")


def test_request_is_schema_constrained_and_keeps_document_out_of_instructions(calls):
    profile, document = example_profile(), example_document()
    reply = json.dumps(reply_for(profile))
    recorded = calls(completed(reply))
    assert provider().extract(profile, {}, document) == reply
    request, timeout = recorded[0]
    body = json.loads(request.data)
    assert timeout == providers.PROVIDER_TIMEOUT_SECONDS < 60
    assert request.get_header("Authorization") == f"Bearer {SECRET}"
    assert body["model"] == "test-model"
    assert body["store"] is False
    output_format = body["text"]["format"]
    assert output_format["type"] == "json_schema" and output_format["strict"] is True
    schema = output_format["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]["fields"]["required"]) == {
        field.key for field in profile.scalar_fields
    }
    assert "Demo Paper" not in body["instructions"]
    assert "Demo Paper" in body["input"][0]["content"][0]["text"]


def test_option_keys_become_an_enum(calls):
    profile = example_profile()
    recorded = calls(completed(json.dumps(reply_for(profile))))
    provider().extract(profile, {"supplier": ["a", "b"]}, example_document())
    schema = json.loads(recorded[0][0].data)["text"]["format"]["schema"]
    supplier = schema["properties"]["fields"]["properties"]["supplier"]
    assert supplier["properties"]["value"]["enum"] == ["a", "b", None]


@pytest.mark.parametrize(
    ("status", "code", "retryable"),
    [
        (429, "AI_RATE_LIMITED", True),
        (500, "AI_UPSTREAM_ERROR", True),
        (503, "AI_UPSTREAM_ERROR", True),
        (401, "AI_AUTH_FAILED", False),
        (400, "AI_REQUEST_REJECTED", False),
    ],
)
def test_http_failures_map_to_safe_codes(calls, status, code, retryable):
    body = io.BytesIO(f'{{"error": "echo {SECRET} and document text"}}'.encode())
    calls(HTTPError(providers.OPENAI_RESPONSES_URL, status, "error", {}, body))
    with pytest.raises(ProviderError) as raised:
        provider().extract(example_profile(), {}, example_document())
    assert (raised.value.code, raised.value.retryable) == (code, retryable)
    assert SECRET not in str(raised.value)
    assert raised.value.__cause__ is None


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (TimeoutError(), "AI_TIMEOUT"),
        (URLError(TimeoutError()), "AI_TIMEOUT"),
        (URLError(ConnectionRefusedError()), "AI_UNREACHABLE"),
        (ConnectionResetError(), "AI_UNREACHABLE"),
    ],
)
def test_network_failures_are_retryable(calls, error, code):
    calls(error)
    with pytest.raises(ProviderError) as raised:
        provider().extract(example_profile(), {}, example_document())
    assert raised.value.code == code and raised.value.retryable


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"status": "incomplete", "output": []}, "AI_OUTPUT_INVALID"),
        ({"status": "completed", "output": []}, "AI_OUTPUT_INVALID"),
        (
            {
                "status": "completed",
                "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}],
            },
            "AI_REFUSED",
        ),
    ],
)
def test_unusable_replies_are_failures(calls, payload, code):
    calls(payload)
    with pytest.raises(ProviderError) as raised:
        provider().extract(example_profile(), {}, example_document())
    assert raised.value.code == code


def test_oversized_documents_are_rejected_before_any_call(calls):
    recorded = calls(completed("{}"))
    document = NormalizedDocument.model_validate(
        {
            "documentId": str(example_document().document_id),
            "units": [{"id": "u", "text": "x" * 250_000, "page": 1, "sheet": None, "cell": None}],
        }
    )
    with pytest.raises(ProviderError) as raised:
        provider().extract(example_profile(), {}, document)
    assert raised.value.code == "DOCUMENT_TOO_LARGE" and not raised.value.retryable
    assert recorded == []


def test_provider_needs_both_key_and_model(monkeypatch):
    from app.platform.settings import Settings

    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert OpenAIProvider.from_settings(Settings(_env_file=None)) is None
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    assert OpenAIProvider.from_settings(Settings(_env_file=None)).model == "test-model"


def test_fixture_mode_fails_explicitly_for_unknown_documents():
    profile, document = example_profile(), example_document()
    changed = document.model_copy(deep=True)
    changed.units[3].text = changed.units[3].text.replace("55.00", "56.00")
    assert fixture_fingerprint(profile, changed) != fixture_fingerprint(profile, document)
    with pytest.raises(ProviderError) as raised:
        FixtureProvider().extract(profile, {}, changed)
    assert raised.value.code == "FIXTURE_NOT_AVAILABLE" and not raised.value.retryable


def test_fixture_survives_relabelled_profiles_but_not_new_fields():
    profile, document = example_profile(), example_document()
    relabelled = profile.model_copy(deep=True)
    relabelled.version = 2
    relabelled.scalar_fields[0].label = "Invoice no."
    assert FixtureProvider().extract(relabelled, {}, document)
    extended = profile.model_copy(deep=True)
    extended.scalar_fields.append(extended.scalar_fields[0].model_copy(update={"key": "extra"}))
    with pytest.raises(ProviderError):
        FixtureProvider().extract(extended, {}, document)
