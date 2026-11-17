import json
from pathlib import Path

import pytest
from app.platform.contracts import ProfileDefinition
from app.platform.errors import DomainError


def form_and_profile():
    from app.profiles.importer import normalize_form

    form = normalize_form("Invoice", json.loads(Path("contracts/examples/form.json").read_text()))
    value = json.loads(Path("contracts/examples/profile.json").read_text())
    del value["id"], value["version"]
    value["formId"] = str(form.id)
    return form, ProfileDefinition.model_validate(value)


def test_shared_profile_example_validates_without_invoice_specific_logic():
    from app.profiles.validation import validate_profile

    form, profile = form_and_profile()
    validate_profile(profile, form)


@pytest.mark.parametrize(
    "change,code",
    [
        (lambda p: setattr(p.scalar_fields[0], "target_tag", "missing"), "DESTINATION_NOT_FOUND"),
        (lambda p: setattr(p.scalar_fields[0], "type", "decimal"), "INCOMPATIBLE_TYPE"),
        (lambda p: setattr(p.scalar_fields[0], "key", ""), "INVALID_KEY"),
        (lambda p: setattr(p.scalar_fields[0], "label", "  "), "INVALID_LABEL"),
        (lambda p: setattr(p.table_fields[0], "target_tag", "supplier"), "DESTINATION_NOT_FOUND"),
        (
            lambda p: setattr(p.table_fields[0].columns[0], "target_tag", "supplier"),
            "DESTINATION_NOT_FOUND",
        ),
        (lambda p: setattr(p.table_fields[0].columns[0], "type", "money"), "INCOMPATIBLE_TYPE"),
        (
            lambda p: setattr(p.scalar_fields[1], "target_tag", "invoice_number"),
            "DUPLICATE_DESTINATION",
        ),
        (lambda p: p.table_fields[0].columns.clear(), "EMPTY_TABLE"),
        (lambda p: p.scalar_fields.clear() or p.table_fields.clear(), "EMPTY_PROFILE"),
    ],
)
def test_profile_mapping_errors_are_local_and_safe(change, code):
    from app.profiles.validation import validate_profile

    form, profile = form_and_profile()
    change(profile)
    with pytest.raises(DomainError) as error:
        validate_profile(profile, form)
    assert error.value.code == code
    assert error.value.details["fields"][0]["path"]


def test_two_forms_with_distinct_tags_columns_and_options_use_same_profile_contract():
    from app.profiles.importer import normalize_form
    from app.profiles.validation import validate_profile

    form, profile = form_and_profile()
    validate_profile(profile, form)
    other = normalize_form(
        "Travel grant",
        {
            "illustrative": True,
            "sections": [
                {
                    "label": "Journey",
                    "fields": [
                        {"tag": "traveller", "label": "Person", "type": "string", "required": True},
                        {
                            "tag": "category",
                            "label": "Category",
                            "type": "string",
                            "options": [
                                {"key": "rail", "label": "Train"},
                                {"key": "air", "label": "Flight"},
                            ],
                        },
                    ],
                    "tables": [
                        {
                            "tag": "journeys",
                            "label": "Journeys",
                            "columns": [
                                {"tag": "destination", "label": "Destination", "type": "string"},
                                {"tag": "travel_date", "label": "Travel date", "type": "date"},
                            ],
                        }
                    ],
                }
            ],
        },
    )
    second = ProfileDefinition.model_validate(
        {
            "name": "Travel statement",
            "documentKind": "bank_statement",
            "formId": str(other.id),
            "scalarFields": [
                {
                    "key": "person",
                    "label": "Person",
                    "type": "string",
                    "description": "Traveller name",
                    "required": True,
                    "targetTag": "traveller",
                },
                {
                    "key": "category",
                    "label": "Category",
                    "type": "string",
                    "description": "Return rail or air, never Train or Flight",
                    "required": False,
                    "targetTag": "category",
                },
            ],
            "tableFields": [
                {
                    "key": "trips",
                    "label": "Trips",
                    "targetTag": "journeys",
                    "writeMode": "replace",
                    "columns": [
                        {
                            "key": "place",
                            "label": "Place",
                            "type": "string",
                            "description": "Destination",
                            "required": True,
                            "targetTag": "destination",
                        },
                        {
                            "key": "date",
                            "label": "Date",
                            "type": "date",
                            "description": "Journey date",
                            "required": False,
                            "targetTag": "travel_date",
                        },
                    ],
                }
            ],
        }
    )
    validate_profile(second, other)
    assert {f.target_tag for f in profile.scalar_fields}.isdisjoint(
        {f.target_tag for f in second.scalar_fields}
    )
    assert other.fields[1].options[0].key == "rail"
