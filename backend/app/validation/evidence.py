"""Check provider-cited evidence against the normalized document.

Only the source unit is trusted for location: page, sheet and cell are copied
from it, never from the provider. Quotes are compared after collapsing
whitespace because OCR and spreadsheet normalization break lines differently
from how a model reproduces them; any other difference makes a quote unverified.
"""

from dataclasses import dataclass, field

from app.platform.contracts import NormalizedDocument, SourceRef, SourceUnit
from app.validation.values import collapse_whitespace


@dataclass
class CitedEvidence:
    unit_id: str
    quote: str | None


@dataclass
class ResolvedEvidence:
    sources: list[SourceRef] = field(default_factory=list)
    supporting_texts: list[str] = field(default_factory=list)
    unknown_units: bool = False
    unverified_quotes: bool = False


def resolve_evidence(
    document: NormalizedDocument, units: dict[str, SourceUnit], cited: list[CitedEvidence]
) -> ResolvedEvidence:
    resolved = ResolvedEvidence()
    seen: set[tuple[str, str | None]] = set()
    for evidence in cited:
        unit = units.get(evidence.unit_id)
        if unit is None:
            # A fabricated unit ID has no location to show; dropping it keeps the
            # review screen from linking to evidence that does not exist.
            resolved.unknown_units = True
            continue
        quote = evidence.quote
        if quote is not None and not quote_in_text(quote, unit.text):
            resolved.unverified_quotes = True
            quote = None
        if (unit.id, quote) in seen:
            continue
        seen.add((unit.id, quote))
        resolved.sources.append(
            SourceRef(
                document_id=document.document_id,
                unit_id=unit.id,
                quote=quote,
                page=unit.page,
                sheet=unit.sheet,
                cell=unit.cell,
            )
        )
        # The value must appear in what the provider quoted; without a verified
        # quote the whole unit is the only text that can support it.
        resolved.supporting_texts.append(quote if quote is not None else unit.text)
    return resolved


def quote_in_text(quote: str, text: str) -> bool:
    needle = collapse_whitespace(quote)
    return bool(needle) and needle in collapse_whitespace(text)


def printed_text_supported(printed: str, supporting_texts: list[str]) -> bool:
    """Whether a value copied as printed occurs in its evidence, ignoring case and spacing."""
    needle = collapse_whitespace(printed).casefold()
    return bool(needle) and any(
        needle in collapse_whitespace(text).casefold() for text in supporting_texts
    )
