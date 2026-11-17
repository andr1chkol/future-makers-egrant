import copy
import json
from pathlib import Path

import pytest
from app.platform.errors import DomainError


def sample_form():
    return json.loads(Path("contracts/examples/form.json").read_text())


def test_import_preserves_original_unknown_settings_and_stable_tags():
    from app.profiles.importer import normalize_form

    source = sample_form()
    source["unknownSetting"] = {"html": "<script>alert('private')</script>"}
    untouched = copy.deepcopy(source)
    normalized = normalize_form("Imported form", source)
    assert normalized.original_json == untouched
    assert normalized.is_illustrative
    source["fields"][0]["label"] = "A different display label"
    renamed = normalize_form("Renamed", source)
    assert renamed.fields[0].tag == normalized.fields[0].tag
    assert renamed.fields[0].label != normalized.fields[0].label
    assert normalized.original_json == untouched


def test_sections_options_required_flags_and_duplicate_labels():
    from app.profiles.importer import normalize_form

    source = {
        "illustrative": True,
        "sections": [
            {
                "label": "Budget",
                "fields": [
                    {
                        "tag": "category",
                        "label": "Category",
                        "type": "string",
                        "required": True,
                        "options": [
                            {"key": "travel", "label": "Same"},
                            {"key": "rent", "label": "Same"},
                        ],
                    }
                ],
                "tables": [],
            }
        ],
    }
    form = normalize_form("Sectioned", source)
    assert form.fields[0].required is True
    assert [option.key for option in form.fields[0].options] == ["travel", "rent"]
    assert form.original_json == source


@pytest.mark.parametrize(
    "change,code",
    [
        (lambda value: value.update(isIllustrative=False), "IMPORT_FORMAT_UNVERIFIED"),
        (lambda value: value["fields"].append(value["fields"][0]), "DUPLICATE_TAG"),
        (lambda value: value["fields"][0].update(type="javascript"), "UNSUPPORTED_FIELD_TYPE"),
        (lambda value: value["fields"][0].update(tag="  "), "INVALID_TAG"),
        (lambda value: value["fields"][0].update(required="false"), "INVALID_REQUIRED"),
        (
            lambda value: value["fields"][0].update(
                options=[{"key": "a", "label": "A"}, {"key": "a", "label": "B"}]
            ),
            "DUPLICATE_OPTION_KEY",
        ),
        (
            lambda value: value["fields"][0].update(options=[{"key": "", "label": "A"}]),
            "INVALID_OPTION",
        ),
        (
            lambda value: value["tables"][0]["columns"].append(value["tables"][0]["columns"][0]),
            "DUPLICATE_TAG",
        ),
        (lambda value: value.update(fields="<script>private</script>"), "INVALID_FORM_SHAPE"),
    ],
)
def test_invalid_imports_use_safe_errors(change, code):
    from app.profiles.importer import normalize_form

    value = sample_form()
    change(value)
    with pytest.raises(DomainError) as error:
        normalize_form("Imported form", value)
    assert error.value.status == 422
    assert error.value.code == code
    assert "<script>" not in str(error.value.details)


def test_nonfinite_values_and_excessive_nesting_are_rejected():
    from app.profiles.importer import normalize_form

    for payload in [float("nan"), float("inf")]:
        value = sample_form()
        value["unknown"] = payload
        with pytest.raises(DomainError):
            normalize_form("Invalid JSON", value)
    value = sample_form()
    nested = value
    for _ in range(70):
        nested["unknown"] = {}
        nested = nested["unknown"]
    with pytest.raises(DomainError):
        normalize_form("Deep JSON", value)


@pytest.mark.parametrize("value", ["null\x00byte", "unpaired\ud800surrogate"])
def test_strings_unsupported_by_postgresql_fail_with_safe_import_errors(value):
    from app.profiles.importer import normalize_form

    source = sample_form()
    source["unknownSetting"] = value
    with pytest.raises(DomainError) as error:
        normalize_form("Invalid string", source)
    assert error.value.code == "INVALID_JSON"


@pytest.mark.parametrize("name", ["invoice", "travel"])
def test_delivered_examples_are_normalized_and_preserved(name):
    from app.profiles.importer import normalize_form

    value = json.loads(Path(f"tests/profiles/examples/{name}-form.json").read_text())
    form = normalize_form(name, value)
    assert form.original_json == value
    assert form.fields and form.tables and form.is_illustrative
