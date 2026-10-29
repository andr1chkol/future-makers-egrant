from pydantic import ValidationError as PydanticValidationError

from app.platform.contracts import (
    ExtractedField,
    Extraction,
    FormDefinition,
    Profile,
    ReviewSnapshot,
    warning_identity,
)
from app.platform.errors import DomainError


def invalid(code: str = "INVALID_REVIEW") -> None:
    # Never put user keys, corrected values or source text in errors/logs.
    raise DomainError(code, 422, "Review does not match the pinned profile")


def keyed(items):
    result = {item.key: item for item in items}
    if len(result) != len(items):
        invalid()
    return result


def validate_snapshot(
    snapshot: ReviewSnapshot,
    extraction: Extraction,
    profile: Profile,
    form: FormDefinition,
    *,
    confirming: bool = False,
) -> None:
    if (profile.id, profile.version, profile.form_id) != (
        extraction.profile_id,
        extraction.profile_version,
        form.id,
    ):
        invalid("PROFILE_MISMATCH")
    fields, tables = keyed(snapshot.fields), keyed(snapshot.tables)
    if (
        fields.keys() != keyed(profile.scalar_fields).keys()
        or tables.keys() != keyed(profile.table_fields).keys()
    ):
        invalid()

    def mapped_target(definition, targets):
        matches = [item for item in targets if item.tag == definition.target_tag]
        if len(matches) != 1 or matches[0].type != definition.type:
            invalid("PROFILE_MISMATCH")
        return matches[0]

    def check(value, definition, targets):
        target = mapped_target(definition, targets)
        try:
            ExtractedField(
                key=definition.key,
                type=definition.type,
                value=value,
                status="missing" if value is None else "found",
                sources=[],
            )
        except PydanticValidationError:
            invalid("INVALID_REVIEW_VALUE")
        if value is not None and target.options is not None:
            if not any(value == option.key for option in target.options):
                invalid("INVALID_REVIEW_OPTION")
        if confirming and (definition.required or target.required):
            if value is None or isinstance(value, str) and not value.strip():
                invalid("REQUIRED_REVIEW_VALUE")

    for definition in profile.scalar_fields:
        check(fields[definition.key].value, definition, form.fields)
    original_locations = {
        row.row_id: table.key for table in extraction.tables for row in table.rows
    }
    row_ids = set()
    for definition in profile.table_fields:
        target = next((table for table in form.tables if table.tag == definition.target_tag), None)
        if target is None:
            invalid("PROFILE_MISMATCH")
        for column in definition.columns:
            mapped_target(column, target.columns)
        for row in tables[definition.key].rows:
            # UUID identity survives reorder/deletion; source rows cannot move between tables.
            if (
                row.row_id in row_ids
                or original_locations.get(row.row_id, definition.key) != definition.key
            ):
                invalid("DUPLICATE_REVIEW_ROW")
            row_ids.add(row.row_id)
            cells = keyed(row.cells)
            if cells.keys() != keyed(definition.columns).keys():
                invalid()
            for column in definition.columns:
                check(cells[column.key].value, column, target.columns)
    acknowledged = set(snapshot.acknowledged_warnings)
    warnings = {warning_identity(warning) for warning in extraction.warnings}
    if len(acknowledged) != len(snapshot.acknowledged_warnings) or not acknowledged <= warnings:
        invalid("INVALID_WARNING_ACKNOWLEDGEMENT")
    if confirming and acknowledged != warnings:
        invalid("UNACKNOWLEDGED_WARNINGS")
