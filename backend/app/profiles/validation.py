import re

from app.platform.contracts import FormDefinition, FormField, ProfileDefinition, ProfileField
from app.profiles.importer import check_json, invalid, text


def validate_identity(key: str, label: str, path: str) -> None:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,127}", key):
        raise invalid("INVALID_KEY", f"{path}.key")
    text(label, f"{path}.label", "INVALID_LABEL")


def validate_fields(fields: list[ProfileField], destinations: list[FormField], path: str) -> None:
    targets = {field.tag: field for field in destinations}
    seen_targets = set()
    seen_keys = set()
    for index, field in enumerate(fields):
        field_path = f"{path}.{index}"
        validate_identity(field.key, field.label, field_path)
        if field.key in seen_keys:
            raise invalid("DUPLICATE_KEY", f"{field_path}.key")
        seen_keys.add(field.key)
        if field.target_tag not in targets:
            raise invalid("DESTINATION_NOT_FOUND", f"{field_path}.targetTag")
        if field.target_tag in seen_targets:
            raise invalid("DUPLICATE_DESTINATION", f"{field_path}.targetTag")
        seen_targets.add(field.target_tag)
        if field.type != targets[field.target_tag].type:
            raise invalid("INCOMPATIBLE_TYPE", f"{field_path}.type")
        if len(field.description) > 10_000:
            raise invalid("DESCRIPTION_TOO_LONG", f"{field_path}.description")


def validate_profile(profile: ProfileDefinition, form: FormDefinition) -> None:
    """Validate destinations by scope, never by labels or inferred invoice field names."""
    check_json(profile.model_dump(mode="json"))
    text(profile.name, "name", "INVALID_LABEL")
    text(profile.document_kind, "documentKind", "INVALID_DOCUMENT_KIND")
    if not profile.scalar_fields and not profile.table_fields:
        raise invalid("EMPTY_PROFILE", "scalarFields")
    validate_fields(profile.scalar_fields, form.fields, "scalarFields")
    tables = {table.tag: table for table in form.tables}
    seen_targets = set()
    seen_keys = set()
    for index, table in enumerate(profile.table_fields):
        path = f"tableFields.{index}"
        validate_identity(table.key, table.label, path)
        if table.key in seen_keys:
            raise invalid("DUPLICATE_KEY", f"{path}.key")
        seen_keys.add(table.key)
        if table.target_tag not in tables:
            raise invalid("DESTINATION_NOT_FOUND", f"{path}.targetTag")
        if table.target_tag in seen_targets:
            raise invalid("DUPLICATE_DESTINATION", f"{path}.targetTag")
        seen_targets.add(table.target_tag)
        if not table.columns:
            raise invalid("EMPTY_TABLE", f"{path}.columns")
        validate_fields(table.columns, tables[table.target_tag].columns, f"{path}.columns")
