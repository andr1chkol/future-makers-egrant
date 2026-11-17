"""Deterministic normalization of values copied verbatim from a document.

The provider is asked to copy numbers and dates exactly as printed. Interpreting
them happens here so that ambiguous notations are detected by code rather than
silently resolved by the model.
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

# Active ISO 4217 codes. Funds and precious-metal codes are excluded on purpose:
# they never appear as the currency of a grant document amount.
ISO_CURRENCIES = frozenset(
    """
    AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BRL
    BSD BTN BWP BYN BZD CAD CDF CHF CLP CNY COP CRC CUP CVE CZK DJF DKK DOP DZD EGP
    ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR
    IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL
    LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MYR MZN NAD NGN NIO NOK NPR
    NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD
    SHP SLE SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX
    USD UYU UZS VES VND VUV WST XAF XCD XOF XPF YER ZAR ZMW ZWG
    """.split()
)

# A symbol supports every currency that commonly uses it; "$" alone does not prove USD.
CURRENCY_SYMBOLS = {
    "€": {"EUR"},
    "$": {"USD", "CAD", "AUD", "NZD", "HKD", "SGD", "MXN"},
    "£": {"GBP"},
    "¥": {"JPY", "CNY"},
    "kč": {"CZK"},
    "zł": {"PLN"},
    "ft": {"HUF"},
    "₴": {"UAH"},
    "₽": {"RUB"},
    "lei": {"RON"},
}

MONTHS = {
    # English and Slovak month names, including Slovak genitive forms used in dates.
    **{
        name: number
        for number, names in enumerate(
            [
                ("january", "jan", "januar", "januára", "január"),
                ("february", "feb", "februar", "februára", "február"),
                ("march", "mar", "marec", "marca"),
                ("april", "apr", "apríl", "apríla"),
                ("may", "máj", "mája"),
                ("june", "jun", "jún", "júna"),
                ("july", "jul", "júl", "júla"),
                ("august", "aug", "augusta"),
                ("september", "sep", "sept", "septembra"),
                ("october", "oct", "okt", "október", "októbra"),
                ("november", "nov", "novembra"),
                ("december", "dec", "decembra"),
            ],
            start=1,
        )
        for name in names
    }
}


class AmbiguousValue(ValueError):
    """The printed text has more than one plausible interpretation."""


class UnrecognizedValue(ValueError):
    """The printed text is not a value of the expected type."""


def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def decimal_candidates(printed: str) -> set[Decimal]:
    """Return every reading of a printed number under common European and English notation."""
    match = re.fullmatch(r"(\D*)(\d(?:.*\d)?)(\D*)", collapse_whitespace(printed))
    if match is None:
        raise UnrecognizedValue("Not a number")
    # Currency markers around the number are tolerated; letters inside it are not.
    prefix, text, suffix = match.groups()
    # "12,-" is the usual way to print a whole amount; that dash is not a sign.
    suffix = re.sub(r"^[.,][-−–]", "", suffix)
    # Accounting exports print negatives as "-12,50", "12,50-" or "(12,50)".
    # Dropping such a marker would silently flip the sign of a debit.
    markers = [
        prefix.endswith(("-", "−")),
        suffix.startswith(("-", "−")),
        "(" in prefix and ")" in suffix,
    ]
    stray_signs = re.search(r"[-−]", prefix[:-1] if markers[0] else prefix) or re.search(
        r"[-−]", suffix[1:] if markers[1] else suffix
    )
    if sum(markers) > 1 or stray_signs:
        raise UnrecognizedValue("Conflicting or detached sign markers")
    sign = "-" if any(markers) else ""
    text = re.sub(r"(?<=\d)[   '’](?=\d{3}(\D|$))", "", text)
    if not re.fullmatch(r"\d[\d.,]*", text):
        raise UnrecognizedValue("Not a number")

    def read(integer: str, fraction: str = "") -> Decimal:
        return Decimal(f"{sign}{integer}.{fraction}" if fraction else f"{sign}{integer}")

    def grouped(integer: str, separator: str) -> str | None:
        if re.fullmatch(rf"\d{{1,3}}(\{separator}\d{{3}})+", integer):
            return integer.replace(separator, "")
        return None

    commas, dots = text.count(","), text.count(".")
    if not commas and not dots:
        return {read(text)}
    if commas and dots:
        decimal_separator = "," if text.rfind(",") > text.rfind(".") else "."
        group_separator = "." if decimal_separator == "," else ","
        integer, fraction = text.rsplit(decimal_separator, 1)
        if group_separator in fraction or decimal_separator in integer:
            raise UnrecognizedValue("Mixed separators")
        plain = grouped(integer, group_separator)
        if plain is None:
            raise UnrecognizedValue("Invalid digit grouping")
        return {read(plain, fraction)}
    separator = "," if commas else "."
    if text.count(separator) > 1:
        plain = grouped(text, separator)
        if plain is None:
            raise UnrecognizedValue("Invalid digit grouping")
        return {read(plain)}
    integer, fraction = text.split(separator)
    readings = {read(integer, fraction)}
    # "1,234" or "1.234" is a thousands group in one notation and a decimal in the other.
    if len(fraction) == 3 and integer != "0" and len(integer) <= 3:
        readings.add(read(integer + fraction))
    return readings


def normalize_decimal(printed: str, min_places: int = 1) -> str:
    """Convert a printed number to the canonical decimal string used by the contract."""
    readings = decimal_candidates(printed)
    if len(readings) > 1:
        raise AmbiguousValue("Thousands separator or decimal point")
    (value,) = readings
    return canonical_decimal(value, min_places)


def canonical_decimal(value: Decimal, min_places: int) -> str:
    places = max(-value.as_tuple().exponent, min_places, 0)
    try:
        return f"{value.quantize(Decimal(1).scaleb(-places)):f}"
    except InvalidOperation as error:
        raise UnrecognizedValue("Number out of range") from error


def decimal_places(canonical: str) -> int:
    return len(canonical.partition(".")[2])


def date_candidates(printed: str) -> set[date]:
    """Return every calendar date the printed text can denote.

    Dot and dash separated day-first dates are unambiguous in the Slovak documents
    this product handles. Slash dates are read both ways because US-formatted
    receipts also occur. Two-digit years are rejected rather than guessed.
    A time of day after the date, as printed on receipts, is ignored.
    """
    text = collapse_whitespace(printed).strip().rstrip(".").lower()
    text = re.sub(r"\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s?(?:h|hod\.?|am|pm))?$", "", text)

    def valid(year: int, month: int, day: int) -> set[date]:
        try:
            return {date(year, month, day)}
        except ValueError:
            return set()

    if match := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text):
        year, month, day = map(int, match.groups())
        readings = valid(year, month, day)
    elif match := re.fullmatch(r"(\d{1,2})\s?[.\-]\s?(\d{1,2})\s?[.\-]\s?(\d{4})", text):
        day, month, year = map(int, match.groups())
        readings = valid(year, month, day)
    elif match := re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text):
        first, second, year = map(int, match.groups())
        readings = valid(year, second, first) | valid(year, first, second)
    elif match := re.fullmatch(r"(\d{1,2})\.?\s+([^\W\d_]+)\.?,?\s+(\d{4})", text):
        day, month_name, year = match.groups()
        month = MONTHS.get(month_name)
        readings = valid(int(year), month, int(day)) if month else set()
    elif match := re.fullmatch(r"([^\W\d_]+)\.?\s+(\d{1,2}),?\s+(\d{4})", text):
        month_name, day, year = match.groups()
        month = MONTHS.get(month_name)
        readings = valid(int(year), month, int(day)) if month else set()
    else:
        readings = set()
    if not readings:
        raise UnrecognizedValue("Not a calendar date")
    return readings


def normalize_date(printed: str) -> str:
    readings = date_candidates(printed)
    if len(readings) > 1:
        raise AmbiguousValue("Day and month order")
    (value,) = readings
    return value.isoformat()


def currencies_in_text(text: str, *, include_ambiguous: bool = True) -> set[str]:
    """Currencies a document visibly mentions, by ISO code or by symbol."""
    lowered = text.lower()
    # Case-sensitive so ordinary words do not match; camelCase headers such as
    # "totalEUR" in spreadsheet exports still count as a mention.
    found = {code for code in ISO_CURRENCIES if re.search(rf"(?<![A-Z]){code}(?![A-Z])", text)}
    for symbol, codes in CURRENCY_SYMBOLS.items():
        if not include_ambiguous and len(codes) > 1:
            continue
        if symbol.isalpha():
            if re.search(rf"(?<![^\W\d_]){re.escape(symbol)}(?![^\W\d_])", lowered):
                found |= codes
        elif symbol in text:
            found |= codes
    return found
