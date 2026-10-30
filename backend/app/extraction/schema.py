"""Profile-derived output schema for the AI provider and a strict parser for its replies.

Values are requested exactly as printed so that `app.validation.values` decides
how to interpret numbers and dates. The parser accepts nothing the schema does
not describe: provider output is untrusted even when structured output is on.
"""

import json
from dataclasses import dataclass

from app.platform.contracts import Profile, ProfileField
from app.validation.evidence import CitedEvidence

MAX_ROWS_PER_TABLE = 500
MAX_EVIDENCE_PER_VALUE = 10

# Option keys permitted for string fields, keyed by scalar key or "table.column".
OptionKeys = dict[str, list[str]]


class ProviderOutputError(ValueError):
    """The provider reply does not match the requested schema."""


@dataclass
class RawValue:
    printed: str | bool | None
    currency: str | None
    evidence: list[CitedEvidence]


@dataclass
class RawOutput:
    fields: dict[str, RawValue]
    tables: dict[str, list[dict[str, RawValue]]]


def option_scope(field_key: str, table_key: str | None = None) -> str:
    return f"{table_key}.{field_key}" if table_key else field_key


def build_output_schema(profile: Profile, options: OptionKeys) -> dict:
    """JSON Schema in the subset accepted by OpenAI strict structured output."""
    tables = {
        table.key: closed_object(
            {
                "rows": {
                    "type": "array",
                    "description": f"{table.label}: one entry per line item, in document order",
                    "items": closed_object(
                        {
                            "cells": closed_object(
                                {
                                    column.key: value_schema(
                                        column, options.get(option_scope(column.key, table.key))
                                    )
                                    for column in table.columns
                                }
                            )
                        }
                    ),
                }
            }
        )
        for table in profile.table_fields
    }
    return closed_object(
        {
            "fields": closed_object(
                {
                    field.key: value_schema(field, options.get(option_scope(field.key)))
                    for field in profile.scalar_fields
                }
            ),
            "tables": closed_object(tables),
        }
    )


def closed_object(properties: dict) -> dict:
    # Strict mode requires every property to be listed as required; optionality
    # is expressed through nullable types instead.
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def value_schema(field: ProfileField, option_keys: list[str] | None) -> dict:
    if field.type == "money":
        value = closed_object(
            {
                "amount": {
                    "type": ["string", "null"],
                    "description": "Amount exactly as printed, without conversion",
                },
                "currency": {
                    "type": ["string", "null"],
                    "description": (
                        "ISO 4217 code the document states for this amount, its column "
                        "or the whole document, else null"
                    ),
                },
            }
        )
    elif field.type == "boolean":
        value = {"type": ["boolean", "null"]}
    elif option_keys:
        value = {"type": ["string", "null"], "enum": [*option_keys, None]}
    else:
        value = {"type": ["string", "null"], "description": "Exactly as printed"}
    described = closed_object(
        {
            "value": value,
            "evidence": {
                "type": "array",
                "items": closed_object(
                    {"unitId": {"type": "string"}, "quote": {"type": ["string", "null"]}}
                ),
            },
        }
    )
    described["description"] = f"{field.label} ({field.type}): {field.description}"
    return described


def parse_provider_output(text: str, profile: Profile) -> RawOutput:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as error:
        raise ProviderOutputError("Reply is not JSON") from error
    root = expect_object(data, {"fields", "tables"})
    fields_data = expect_object(root["fields"], {field.key for field in profile.scalar_fields})
    tables_data = expect_object(root["tables"], {table.key for table in profile.table_fields})
    fields = {
        field.key: parse_value(fields_data[field.key], field) for field in profile.scalar_fields
    }
    tables = {}
    for table in profile.table_fields:
        rows = expect_object(tables_data[table.key], {"rows"})["rows"]
        if not isinstance(rows, list) or len(rows) > MAX_ROWS_PER_TABLE:
            raise ProviderOutputError("Table rows must be a bounded list")
        column_keys = {column.key for column in table.columns}
        parsed_rows = []
        for row in rows:
            cells = expect_object(expect_object(row, {"cells"})["cells"], column_keys)
            parsed_rows.append(
                {column.key: parse_value(cells[column.key], column) for column in table.columns}
            )
        tables[table.key] = parsed_rows
    return RawOutput(fields=fields, tables=tables)


def expect_object(data: object, keys: set[str]) -> dict:
    if not isinstance(data, dict) or set(data) != keys:
        raise ProviderOutputError("Unexpected or missing keys")
    return data


def parse_value(data: object, field: ProfileField) -> RawValue:
    item = expect_object(data, {"value", "evidence"})
    value, currency = item["value"], None
    if field.type == "money":
        if value is not None:
            money = expect_object(value, {"amount", "currency"})
            value, currency = money["amount"], money["currency"]
            if not isinstance(value, str | None) or not isinstance(currency, str | None):
                raise ProviderOutputError("Money parts must be strings or null")
    elif field.type == "boolean":
        if not isinstance(value, bool | None):
            raise ProviderOutputError("Boolean expected")
    elif not isinstance(value, str | None):
        raise ProviderOutputError("String expected")
    # Option keys are checked during assembly, where a wrong key becomes a warning.
    evidence = item["evidence"]
    if not isinstance(evidence, list) or len(evidence) > MAX_EVIDENCE_PER_VALUE:
        raise ProviderOutputError("Evidence must be a bounded list")
    cited = []
    for entry in evidence:
        source = expect_object(entry, {"unitId", "quote"})
        if not isinstance(source["unitId"], str) or not isinstance(source["quote"], str | None):
            raise ProviderOutputError("Evidence entries need a unit ID and optional quote")
        cited.append(CitedEvidence(unit_id=source["unitId"], quote=source["quote"]))
    return RawValue(printed=value, currency=currency, evidence=cited)
