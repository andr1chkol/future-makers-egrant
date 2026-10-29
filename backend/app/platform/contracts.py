"""Public wire DTOs. Generate OpenAPI and TypeScript from these definitions."""

import json
from datetime import date
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, model_validator
from pydantic.alias_generators import to_camel

DecimalString = Annotated[str, Field(pattern=r"^-?(0|[1-9][0-9]*)\.[0-9]+$")]
FieldType = Literal["string", "decimal", "date", "boolean", "money"]
FieldStatus = Literal["found", "missing", "needs_review"]
JobKind = Literal["document.process", "extraction.process", "submission.apply"]


class DTO(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Money(DTO):
    amount: DecimalString
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


Value = str | StrictBool | Money | None


class DomainErrorDTO(DTO):
    code: str
    message: str
    details: dict[str, object] | None = None


class ErrorEnvelope(DTO):
    error: DomainErrorDTO


class Success[T](DTO):
    data: T


class Pagination(DTO):
    limit: Annotated[int, Field(ge=1, le=200)] = 50
    offset: Annotated[int, Field(ge=0)] = 0
    total: Annotated[int, Field(ge=0)]


class Page[T](Success[list[T]]):
    pagination: Pagination


class Warning(DTO):
    code: str
    message: str
    field_key: str | None = None
    table_key: str | None = None
    row_id: UUID | None = None


def warning_identity(warning: Warning) -> str:
    """Include message and location so distinct warnings cannot share acknowledgement."""
    canonical = json.dumps(
        warning.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode()).hexdigest()


class SourceRef(DTO):
    document_id: UUID
    unit_id: str
    quote: str | None
    page: Annotated[int, Field(ge=1)] | None
    sheet: str | None
    cell: str | None


class SourceUnit(DTO):
    id: str
    text: str
    page: Annotated[int, Field(ge=1)] | None
    sheet: str | None
    cell: str | None


class NormalizedDocument(DTO):
    document_id: UUID
    units: list[SourceUnit]


class Document(DTO):
    id: UUID
    filename: str
    media_type: str
    status: Literal["uploaded", "processing", "ready", "failed"]
    content_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    duplicate_of: UUID | None
    created_at: AwareDatetime
    page_count: Annotated[int, Field(ge=1)] | None
    warnings: list[Warning]
    error: DomainErrorDTO | None


class Option(DTO):
    key: str
    label: str


class FormField(DTO):
    tag: str
    label: str
    type: FieldType
    required: bool
    options: list[Option] | None


class FormTable(DTO):
    tag: str
    label: str
    columns: list[FormField]


class FormDefinition(DTO):
    id: UUID
    name: str
    is_illustrative: bool
    original_json: dict[str, object]
    fields: list[FormField]
    tables: list[FormTable]


class CreateForm(DTO):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    definition: dict[str, object]


class ProfileField(DTO):
    key: str
    label: str
    type: FieldType
    description: str
    required: bool
    target_tag: str


class ProfileTable(DTO):
    key: str
    label: str
    target_tag: str
    write_mode: Literal["append", "replace"]
    columns: list[ProfileField]


class ProfileDefinition(DTO):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    document_kind: str
    form_id: UUID
    scalar_fields: list[ProfileField]
    table_fields: list[ProfileTable]

    @model_validator(mode="after")
    def unique_keys(self):
        scopes = [self.scalar_fields, self.table_fields]
        scopes.extend(table.columns for table in self.table_fields)
        for scope in scopes:
            keys = [item.key for item in scope]
            if len(keys) != len(set(keys)):
                raise ValueError("Keys must be unique within their scope")
        return self


class Profile(ProfileDefinition):
    id: UUID
    version: Annotated[int, Field(ge=1)]


class CreateProfileVersion(ProfileDefinition):
    expected_version: Annotated[int, Field(ge=1)]


class ExtractedField(DTO):
    key: str
    type: FieldType
    value: Value
    status: FieldStatus
    sources: list[SourceRef]

    @model_validator(mode="after")
    def typed_value(self):
        if self.value is None:
            if self.status != "missing":
                raise ValueError("Null extraction values must have missing status")
            return self
        if self.status == "missing":
            raise ValueError("Missing status requires null")
        from pydantic import TypeAdapter

        if self.type == "money":
            self.value = TypeAdapter(Money).validate_python(self.value)
        elif self.type == "boolean":
            TypeAdapter(StrictBool).validate_python(self.value)
        elif self.type == "decimal":
            TypeAdapter(DecimalString).validate_python(self.value)
        elif self.type == "date":
            if (
                not isinstance(self.value, str)
                or date.fromisoformat(self.value).isoformat() != self.value
            ):
                raise ValueError("Invalid calendar date")
        elif not isinstance(self.value, str):
            raise ValueError("String value required")
        return self


class ExtractedRow(DTO):
    row_id: UUID
    cells: list[ExtractedField]


class ExtractedTable(DTO):
    key: str
    rows: list[ExtractedRow]


class Extraction(DTO):
    id: UUID
    document_id: UUID
    profile_id: UUID
    profile_version: Annotated[int, Field(ge=1)]
    status: Literal["queued", "running", "ready", "failed"]
    mode: Literal["live", "fixture"]
    fields: list[ExtractedField]
    tables: list[ExtractedTable]
    warnings: list[Warning]
    error: DomainErrorDTO | None
    created_at: AwareDatetime


class CreateExtractions(DTO):
    document_ids: Annotated[list[UUID], Field(min_length=1, max_length=100)]
    profile_id: UUID
    profile_version: Annotated[int, Field(ge=1)]


class QueuedExtraction(DTO):
    id: UUID
    document_id: UUID
    status: Literal["queued", "running", "ready", "failed"]


class ExtractionBatch(DTO):
    extractions: list[QueuedExtraction]


class ReviewField(DTO):
    key: str
    value: Value


class ReviewRow(DTO):
    row_id: UUID
    cells: list[ReviewField]


class ReviewTable(DTO):
    key: str
    rows: list[ReviewRow]


class ReviewSnapshot(DTO):
    fields: list[ReviewField]
    tables: list[ReviewTable]
    acknowledged_warnings: list[Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]]


class SaveReview(ReviewSnapshot):
    expected_revision: Annotated[int, Field(ge=0)]


class ConfirmReview(DTO):
    expected_revision: Annotated[int, Field(ge=0)]


class Review(ReviewSnapshot):
    extraction_id: UUID
    revision: Annotated[int, Field(ge=0)]
    status: Literal["draft", "confirmed"]
    confirmed_at: AwareDatetime | None


class TargetContext(DTO):
    application_id: str | None


class CreateSubmission(DTO):
    review_id: UUID
    review_revision: Annotated[int, Field(ge=1)]
    mode: Literal["export", "egrant"]
    target_context: TargetContext
    acknowledge_overwrite: bool


class SubmissionField(DTO):
    target_tag: str
    value: Value


class SubmissionRow(DTO):
    row_id: UUID
    values: dict[str, Value]


class SubmissionTable(DTO):
    target_tag: str
    write_mode: Literal["append", "replace"]
    rows: list[SubmissionRow]


class SubmissionPayload(DTO):
    form_id: UUID
    profile_id: UUID
    profile_version: Annotated[int, Field(ge=1)]
    fields: list[SubmissionField]
    tables: list[SubmissionTable]


class Submission(DTO):
    id: UUID
    review_id: UUID
    review_revision: Annotated[int, Field(ge=1)]
    mode: Literal["export", "egrant"]
    target_context: TargetContext
    status: Literal["prepared", "exported", "applying", "applied", "failed", "unknown"]
    payload: SubmissionPayload
    external_receipt: dict[str, object] | None
    created_at: AwareDatetime
    error: DomainErrorDTO | None


class Capabilities(DTO):
    ocr_configured: bool
    ai_configured: bool
    egrant_configured: bool
    mode: Literal["live", "fixture"]


class Login(DTO):
    access_code: Annotated[str, Field(min_length=1, max_length=512)]


class SessionInfo(DTO):
    authenticated: bool
    mode: Literal["live", "fixture"]
