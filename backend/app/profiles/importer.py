"""Normalize the illustrative format; real eGrant exports require a verified adapter."""

import json
import math
from copy import deepcopy
from typing import get_args
from uuid import uuid4

from app.platform.contracts import FieldType, FormDefinition, FormField, FormTable, Option
from app.platform.errors import DomainError


def invalid(code: str, path: str) -> DomainError:
    # Paths are structural indexes, never imported tags, labels or personal values.
    return DomainError(
        code,
        422,
        "Invalid form or profile configuration",
        {
            "fields": [{"path": path, "code": code}],
        },
    )


def check_json(value: object, depth: int = 0) -> None:
    if depth > 64:
        raise invalid("IMPORT_TOO_DEEP", "definition")
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise invalid("INVALID_JSON", "definition")
            check_json(key, depth + 1)
            check_json(nested, depth + 1)
    elif isinstance(value, list):
        for nested in value:
            check_json(nested, depth + 1)
    elif isinstance(value, str):
        # JSONB cannot store NUL or unpaired surrogates; reject before the database boundary.
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise invalid("INVALID_JSON", "definition") from error
        if "\x00" in value:
            raise invalid("INVALID_JSON", "definition")
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise invalid("INVALID_JSON", "definition")
    elif value is not None and not isinstance(value, (str, int, bool)):
        raise invalid("INVALID_JSON", "definition")


def text(value: object, path: str, code: str = "INVALID_FORM_SHAPE") -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 10_000:
        raise invalid(code, path)
    return value


def array(value: object, path: str) -> list:
    if not isinstance(value, list):
        raise invalid("INVALID_FORM_SHAPE", path)
    return value


def normalize_field(raw: object, path: str) -> FormField:
    if not isinstance(raw, dict):
        raise invalid("INVALID_FORM_SHAPE", path)
    tag = text(raw.get("tag"), f"{path}.tag", "INVALID_TAG")
    label = text(raw.get("label"), f"{path}.label")
    field_type = raw.get("type")
    if field_type not in get_args(FieldType):
        raise invalid("UNSUPPORTED_FIELD_TYPE", f"{path}.type")
    required = raw.get("required", False)
    if not isinstance(required, bool):
        raise invalid("INVALID_REQUIRED", f"{path}.required")
    options = None
    if raw.get("options") is not None:
        if field_type != "string":
            raise invalid("INVALID_OPTION", f"{path}.options")
        options = []
        seen = set()
        for index, option in enumerate(array(raw["options"], f"{path}.options")):
            option_path = f"{path}.options.{index}"
            if not isinstance(option, dict):
                raise invalid("INVALID_OPTION", option_path)
            key = text(option.get("key"), option_path, "INVALID_OPTION")
            if key in seen:
                raise invalid("DUPLICATE_OPTION_KEY", option_path)
            seen.add(key)
            # Option keys are extraction values; labels are presentation only.
            options.append(Option(key=key, label=text(option.get("label"), option_path)))
    return FormField(tag=tag, label=label, type=field_type, required=required, options=options)


def normalize_form(name: str, definition: dict) -> FormDefinition:
    """Preserve the entire import while normalizing only the documented illustrative structure."""
    check_json(name)
    check_json(definition)
    if len(json.dumps(definition, ensure_ascii=True).encode()) > 2 * 1024 * 1024:
        raise DomainError("IMPORT_TOO_LARGE", 413, "Form definition exceeds the import limit")
    if definition.get("isIllustrative", definition.get("illustrative")) is not True:
        raise invalid("IMPORT_FORMAT_UNVERIFIED", "definition")
    text(name, "name")
    fields: list[FormField] = []
    tables: list[FormTable] = []
    seen = set()

    def add_tag(tag: str, path: str, scope: set) -> None:
        # Destination addresses come from explicit tags and never from editable labels.
        if tag in scope:
            raise invalid("DUPLICATE_TAG", path)
        scope.add(tag)

    def section(raw: dict, path: str) -> None:
        for index, value in enumerate(array(raw.get("fields", []), f"{path}.fields")):
            field_path = f"{path}.fields.{index}"
            field = normalize_field(value, field_path)
            add_tag(field.tag, f"{field_path}.tag", seen)
            fields.append(field)
        for index, value in enumerate(array(raw.get("tables", []), f"{path}.tables")):
            table_path = f"{path}.tables.{index}"
            if not isinstance(value, dict):
                raise invalid("INVALID_FORM_SHAPE", table_path)
            tag = text(value.get("tag"), f"{table_path}.tag", "INVALID_TAG")
            add_tag(tag, f"{table_path}.tag", seen)
            columns = []
            column_tags = set()
            for column_index, column in enumerate(array(value.get("columns"), table_path)):
                column_path = f"{table_path}.columns.{column_index}"
                field = normalize_field(column, column_path)
                add_tag(field.tag, column_path, column_tags)
                columns.append(field)
            if not columns:
                raise invalid("EMPTY_TABLE", f"{table_path}.columns")
            tables.append(
                FormTable(tag=tag, label=text(value.get("label"), table_path), columns=columns)
            )
        for index, child in enumerate(array(raw.get("sections", []), f"{path}.sections")):
            if not isinstance(child, dict):
                raise invalid("INVALID_FORM_SHAPE", f"{path}.sections.{index}")
            section(child, f"{path}.sections.{index}")

    section(definition, "definition")
    if not fields and not tables:
        raise invalid("EMPTY_FORM", "definition")
    # Unknown configuration is kept verbatim rather than reconstructed from our limited view.
    return FormDefinition(
        id=uuid4(),
        name=name,
        is_illustrative=True,
        original_json=deepcopy(definition),
        fields=fields,
        tables=tables,
    )
