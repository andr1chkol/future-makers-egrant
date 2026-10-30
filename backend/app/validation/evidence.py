"""Check provider-cited evidence against the normalized document.

Only the source unit is trusted for location: page, sheet and cell are copied
from it, never from the provider. Matching tolerates whitespace changes from
OCR line breaks, but stored quotes always use the exact matching source span.
Any other difference makes a quote unverified.
"""

import re
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
        if quote is not None:
            quote = source_excerpt(quote, unit.text)
            if quote is None:
                resolved.unverified_quotes = True
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


def source_excerpt(quote: str, text: str) -> str | None:
    words = quote.split()
    if not words:
        return None
    match = re.search(r"\s+".join(re.escape(word) for word in words), text)
    return match.group() if match else None


def printed_text_supported(printed: str, supporting_texts: list[str]) -> bool:
    """Whether a value copied as printed occurs in its evidence, ignoring case and spacing.

    A value that starts or ends with a digit must not continue a longer number in
    the evidence, so "234,50" is not supported by "1.234,50" and "1.3.2026" is
    not supported by "11.3.2026". Space-grouped numbers are not treated as
    continuations because table columns are often separated by single spaces.
    """
    needle = collapse_whitespace(printed).casefold()
    if not needle:
        return False
    before = r"(?<!\d)(?<!\d[.,'’])" if needle[0].isdigit() else ""
    after = r"(?!\d)(?![.,'’]\d)" if needle[-1].isdigit() else ""
    pattern = re.compile(before + re.escape(needle) + after)
    return any(pattern.search(collapse_whitespace(text).casefold()) for text in supporting_texts)


def printed_sign_supported(printed: str, source_texts: list[str]) -> bool:
    """A cropped quote must not hide a debit sign in the original unit."""
    needle = collapse_whitespace(printed).casefold()
    if not needle:
        return False
    for text in source_texts:
        text = collapse_whitespace(text).casefold()
        for match in re.finditer(re.escape(needle), text):
            before, after = text[: match.start()], text[match.end() :]
            if before.rstrip().endswith(("-", "−", "(")):
                continue
            if after.lstrip().startswith(("-", "−", ")")):
                continue
            if needle[0].isdigit() and before and before[-1].isdigit():
                continue
            if needle[-1].isdigit() and after and after[0].isdigit():
                continue
            return True
    return False
