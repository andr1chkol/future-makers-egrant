"""Turn a parsed provider reply into contract fields, rows and warnings.

Every value is normalized deterministically and checked against its cited
evidence. A value that cannot be interpreted becomes null with a warning; a
value that is readable but weakly supported keeps its reading and is marked
needs_review. Nothing is filled in or corrected here.
"""

import json
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.extraction.schema import OptionKeys, RawOutput, RawValue, option_scope
from app.platform.contracts import (
    ExtractedField,
    ExtractedRow,
    ExtractedTable,
    Money,
    NormalizedDocument,
    Profile,
    ProfileField,
    SourceUnit,
    Warning,
    warning_identity,
)
from app.validation.evidence import (
    printed_sign_supported,
    printed_text_supported,
    resolve_evidence,
)
from app.validation.rules import check_extraction_rules
from app.validation.values import (
    ISO_CURRENCIES,
    AmbiguousValue,
    UnrecognizedValue,
    currencies_in_text,
    normalize_date,
    normalize_decimal,
)

MESSAGES = {
    "REQUIRED_VALUE_MISSING": "A required value was not found in the document",
    "MISSING_OPTIONAL_VALUE": "An optional value was not found in the document",
    "VALUE_UNREADABLE": "The printed value could not be read as the expected type",
    "NUMBER_AMBIGUOUS": "The number can be read with either separator as decimal point",
    "DATE_AMBIGUOUS": "The date can be read with day and month in either order",
    "OPTION_NOT_PERMITTED": "The proposed value is not one of the permitted options",
    "CURRENCY_AMBIGUOUS": "The currency symbol does not identify a single currency",
    "CURRENCY_MISSING": "The amount has no currency stated in the document",
    "CURRENCY_INVALID": "The currency is not a supported ISO 4217 code",
    "CURRENCY_NOT_IN_DOCUMENT": "The currency is not mentioned in the document",
    "SOURCE_UNIT_UNKNOWN": "Cited evidence refers to a part of the document that does not exist",
    "QUOTE_NOT_IN_SOURCE": "The cited quote does not occur in the referenced part of the document",
    "EVIDENCE_MISSING": "The value has no supporting evidence in the document",
    "VALUE_NOT_IN_EVIDENCE": "The value does not occur in its cited evidence",
    "EMPTY_ROW_DROPPED": "A table row without any values was ignored",
    "DUPLICATE_ROW": "This row repeats another row with identical values and evidence",
}


class ValueRejected(ValueError):
    """A printed value that cannot become a contract value; `code` names the warning."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class AssembledExtraction:
    fields: list[ExtractedField]
    tables: list[ExtractedTable]
    warnings: list[Warning] = field(default_factory=list)


@dataclass
class DocumentContext:
    document: NormalizedDocument
    options: OptionKeys
    units: dict[str, SourceUnit] = field(init=False)
    currencies: set[str] = field(init=False)
    definite_currencies: set[str] = field(init=False)

    def __post_init__(self):
        self.units = {unit.id: unit for unit in self.document.units}
        text = "\n".join(unit.text for unit in self.document.units)
        self.currencies = currencies_in_text(text)
        self.definite_currencies = currencies_in_text(text, include_ambiguous=False)


def assemble_extraction(
    raw: RawOutput, profile: Profile, document: NormalizedDocument, options: OptionKeys
) -> AssembledExtraction:
    context = DocumentContext(document, options)
    warnings: list[Warning] = []
    fields = []
    for spec in profile.scalar_fields:
        extracted, field_warnings = assemble_value(raw.fields[spec.key], spec, context)
        fields.append(extracted)
        warnings.extend(field_warnings)
        if extracted.value is None and not field_warnings:
            code = "REQUIRED_VALUE_MISSING" if spec.required else "MISSING_OPTIONAL_VALUE"
            warnings.append(warning(code, field_key=spec.key))

    tables = []
    for table_spec in profile.table_fields:
        rows: list[ExtractedRow] = []
        seen_rows: dict[str, UUID] = {}
        dropped_empty = False
        for raw_row in raw.tables[table_spec.key]:
            # Row IDs are minted once here and persisted, so reads never renumber rows.
            row_id = uuid4()
            cells, row_warnings = [], []
            for spec in table_spec.columns:
                cell, cell_warnings = assemble_value(
                    raw_row[spec.key], spec, context, table_key=table_spec.key, row_id=row_id
                )
                cells.append(cell)
                row_warnings.extend(cell_warnings)
                if cell.value is None and not cell_warnings and spec.required:
                    row_warnings.append(
                        warning(
                            "REQUIRED_VALUE_MISSING",
                            field_key=spec.key,
                            table_key=table_spec.key,
                            row_id=row_id,
                        )
                    )
            if all(cell.value is None for cell in cells):
                dropped_empty = True
                continue
            # Identical lines with distinct evidence are genuine repeated items; the
            # same evidence cited twice usually means one line was read twice.
            signature = row_signature(cells)
            if signature in seen_rows:
                row_warnings.append(
                    warning("DUPLICATE_ROW", table_key=table_spec.key, row_id=row_id)
                )
            seen_rows.setdefault(signature, row_id)
            rows.append(ExtractedRow(row_id=row_id, cells=cells))
            warnings.extend(row_warnings)
        if dropped_empty:
            warnings.append(warning("EMPTY_ROW_DROPPED", table_key=table_spec.key))
        tables.append(ExtractedTable(key=table_spec.key, rows=rows))

    warnings.extend(check_extraction_rules(fields, tables))
    return AssembledExtraction(fields=fields, tables=tables, warnings=unique(warnings))


def assemble_value(
    raw: RawValue,
    spec: ProfileField,
    context: DocumentContext,
    table_key: str | None = None,
    row_id: UUID | None = None,
) -> tuple[ExtractedField, list[Warning]]:
    def flagged(code: str) -> Warning:
        return warning(code, field_key=spec.key, table_key=table_key, row_id=row_id)

    evidence = resolve_evidence(context.document, context.units, raw.evidence)
    if raw.printed is None or (isinstance(raw.printed, str) and not raw.printed.strip()):
        return missing(spec), []

    option_keys = context.options.get(option_scope(spec.key, table_key))
    issues: list[str] = []
    try:
        value = normalize(raw, spec, option_keys)
    except AmbiguousValue:
        code = "DATE_AMBIGUOUS" if spec.type == "date" else "NUMBER_AMBIGUOUS"
        return missing(spec, evidence.sources), [flagged(code)]
    except ValueRejected as rejection:
        return missing(spec, evidence.sources), [flagged(rejection.code)]

    if isinstance(value, Money):
        if value.currency not in context.currencies:
            issues.append("CURRENCY_NOT_IN_DOCUMENT")
        elif value.currency not in context.definite_currencies:
            issues.append("CURRENCY_AMBIGUOUS")
    if evidence.unknown_units:
        issues.append("SOURCE_UNIT_UNKNOWN")
    if evidence.unverified_quotes:
        issues.append("QUOTE_NOT_IN_SOURCE")
    if not evidence.sources:
        issues.append("EVIDENCE_MISSING")
    elif (
        isinstance(raw.printed, str)
        and not option_keys
        and (
            not printed_text_supported(raw.printed, evidence.supporting_texts)
            or (
                spec.type in {"decimal", "money"}
                and not printed_sign_supported(
                    raw.printed, [context.units[source.unit_id].text for source in evidence.sources]
                )
            )
        )
    ):
        # Catches values the model produced from instructions or general
        # knowledge while citing a real but unrelated part of the document.
        issues.append("VALUE_NOT_IN_EVIDENCE")

    extracted = ExtractedField(
        key=spec.key,
        type=spec.type,
        value=value,
        status="needs_review" if issues else "found",
        sources=evidence.sources,
    )
    return extracted, [flagged(code) for code in issues]


def normalize(raw: RawValue, spec: ProfileField, option_keys: list[str] | None):
    printed = raw.printed
    if spec.type == "boolean":
        return printed
    if spec.type == "string":
        if option_keys and printed not in option_keys:
            raise ValueRejected("OPTION_NOT_PERMITTED")
        return printed.strip()
    try:
        if spec.type == "decimal":
            return normalize_decimal(printed)
        if spec.type == "date":
            return normalize_date(printed)
        amount = normalize_decimal(printed, min_places=2)
    except UnrecognizedValue as error:
        raise ValueRejected("VALUE_UNREADABLE") from error
    if raw.currency is None:
        raise ValueRejected("CURRENCY_MISSING")
    currency = raw.currency.strip().upper()
    if currency not in ISO_CURRENCIES:
        raise ValueRejected("CURRENCY_INVALID")
    return Money(amount=amount, currency=currency)


def missing(spec: ProfileField, sources=()) -> ExtractedField:
    # Sources stay attached when a printed value was found but not interpretable,
    # so the reviewer can jump straight to it.
    return ExtractedField(
        key=spec.key, type=spec.type, value=None, status="missing", sources=list(sources)
    )


def warning(code: str, **location) -> Warning:
    return Warning(code=code, message=MESSAGES[code], **location)


def row_signature(cells: list[ExtractedField]) -> str:
    return json.dumps(
        [
            [
                cell.key,
                cell.model_dump(mode="json")["value"],
                sorted(s.unit_id for s in cell.sources),
            ]
            for cell in cells
        ],
        sort_keys=True,
    )


def unique(warnings: list[Warning]) -> list[Warning]:
    seen, result = set(), []
    for item in warnings:
        identity = warning_identity(item)
        if identity not in seen:
            seen.add(identity)
            result.append(item)
    return result
