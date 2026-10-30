"""Recheck the confirmed snapshot and mapping at the export boundary."""

from pydantic import ValidationError as PydanticValidationError

from app.platform.contracts import (
    ExtractedField,
    Extraction,
    FormDefinition,
    Profile,
    Review,
    SubmissionPayload,
    warning_identity,
)
from app.platform.errors import ConflictError, ValidationError


def unique(items, attribute):
    values = {getattr(item, attribute): item for item in items}
    if len(values) != len(items):
        raise ValidationError()
    return values


def mapped_fields(definitions, values, targets):
    source = unique(values, "key")
    target = unique(targets, "tag")
    unique(definitions, "key")
    unique(definitions, "target_tag")
    if source.keys() != {field.key for field in definitions}:
        raise ValidationError()
    mapped = []
    for field in definitions:
        destination = target.get(field.target_tag)
        if destination is None or destination.type != field.type:
            raise ValidationError()
        value = source[field.key].value
        required = field.required or destination.required
        if required and (value is None or isinstance(value, str) and not value.strip()):
            raise ValidationError()
        try:
            ExtractedField(
                key=field.key,
                type=field.type,
                value=value,
                status="missing" if value is None else "found",
                sources=[],
            )
        except (PydanticValidationError, ValueError):
            raise ValidationError() from None
        if value is not None and destination.options is not None:
            if value not in [option.key for option in destination.options]:
                raise ValidationError()
        mapped.append({"targetTag": field.target_tag, "value": value})
    if any(
        field.required and field.tag not in {x["targetTag"] for x in mapped} for field in targets
    ):
        raise ValidationError()
    return mapped


def build_submission_payload(
    review: Review,
    extraction: Extraction,
    profile: Profile,
    form: FormDefinition,
) -> SubmissionPayload:
    if (
        review.status != "confirmed"
        or review.confirmed_at is None
        or review.extraction_id != extraction.id
        or extraction.status != "ready"
        or profile.id != extraction.profile_id
        or profile.version != extraction.profile_version
        or form.id != profile.form_id
    ):
        raise ConflictError()
    if set(review.acknowledged_warnings) != {warning_identity(w) for w in extraction.warnings}:
        raise ConflictError()
    fields = mapped_fields(profile.scalar_fields, review.fields, form.fields)
    reviews = unique(review.tables, "key")
    definitions = unique(profile.table_fields, "key")
    destinations = unique(form.tables, "tag")
    unique(profile.table_fields, "target_tag")
    if reviews.keys() != definitions.keys():
        raise ValidationError()
    tables = []
    for definition in profile.table_fields:
        destination = destinations.get(definition.target_tag)
        if destination is None:
            raise ValidationError()
        rows = reviews[definition.key].rows
        unique(rows, "row_id")
        unique(definition.columns, "key")
        column_targets = unique(destination.columns, "tag")
        unique(definition.columns, "target_tag")
        for column in definition.columns:
            if (
                column.target_tag not in column_targets
                or column.type != column_targets[column.target_tag].type
            ):
                raise ValidationError()
        if any(
            column.required and column.tag not in {c.target_tag for c in definition.columns}
            for column in destination.columns
        ):
            raise ValidationError()
        tables.append(
            {
                "targetTag": definition.target_tag,
                "writeMode": definition.write_mode,
                "rows": [
                    {
                        "rowId": row.row_id,
                        "values": {
                            field["targetTag"]: field["value"]
                            for field in mapped_fields(
                                definition.columns, row.cells, destination.columns
                            )
                        },
                    }
                    for row in rows
                ],
            }
        )
    return SubmissionPayload(
        form_id=form.id,
        profile_id=profile.id,
        profile_version=profile.version,
        fields=fields,
        tables=tables,
    )
