import pytest
from app.validation.evidence import printed_text_supported
from app.validation.values import (
    AmbiguousValue,
    UnrecognizedValue,
    currencies_in_text,
    normalize_date,
    normalize_decimal,
)


@pytest.mark.parametrize(
    ("printed", "canonical"),
    [
        ("12.50", "12.50"),
        ("12,50 €", "12.50"),
        ("1 234,56", "1234.56"),
        ("1 234,56", "1234.56"),
        ("1.234,56", "1234.56"),
        ("1,234.56", "1234.56"),
        ("1.234.567", "1234567.0"),
        ("-650,00", "-650.00"),
        ("−84,35", "-84.35"),
        ("0,125", "0.125"),
        ("10", "10.0"),
        ("EUR 48 600,00", "48600.00"),
        ("12,- €", "12.0"),
        ("650,00-", "-650.00"),
        ("(84,35)", "-84.35"),
        ("€ (1.234,50)", "-1234.50"),
    ],
)
def test_decimal_normalization(printed, canonical):
    assert normalize_decimal(printed) == canonical


def test_money_amounts_keep_at_least_cents():
    assert normalize_decimal("25", min_places=2) == "25.00"
    assert normalize_decimal("0,125", min_places=2) == "0.125"


@pytest.mark.parametrize("printed", ["1,234", "1.234", "12.345"])
def test_thousands_or_decimal_is_ambiguous(printed):
    with pytest.raises(AmbiguousValue):
        normalize_decimal(printed)


@pytest.mark.parametrize(
    "printed",
    ["1O.00", "12,50,1", "abc", "1.2.3", "1,234.5.6", "-12,50-", "(-12,50)", "- 12,50", "12,50--"],
)
def test_ocr_noise_is_not_silently_corrected(printed):
    with pytest.raises(UnrecognizedValue):
        normalize_decimal(printed)


@pytest.mark.parametrize(
    ("printed", "iso"),
    [
        ("2026-10-20", "2026-10-20"),
        ("20.10.2026", "2026-10-20"),
        ("1. 11. 2026", "2026-11-01"),
        ("03-11-2026", "2026-11-03"),
        ("10/29/2026", "2026-10-29"),
        ("29/10/2026", "2026-10-29"),
        ("5. októbra 2026", "2026-10-05"),
        ("20 October 2026", "2026-10-20"),
        ("October 20, 2026", "2026-10-20"),
        ("5/5/2026", "2026-05-05"),
        ("29.10.2026 18:05", "2026-10-29"),
        ("29.10.2026 18:05:12", "2026-10-29"),
        ("10/29/2026 2:32 PM", "2026-10-29"),
    ],
)
def test_date_normalization(printed, iso):
    assert normalize_date(printed) == iso


def test_slash_date_with_both_readings_is_ambiguous():
    with pytest.raises(AmbiguousValue):
        normalize_date("03/04/2026")


@pytest.mark.parametrize(
    "printed", ["31.02.2026", "20.10.26", "next Monday", "2026-13-01", "18:05", "29.10.2026 25"]
)
def test_impossible_or_incomplete_dates_are_rejected(printed):
    with pytest.raises(UnrecognizedValue):
        normalize_date(printed)


def test_currency_mentions():
    assert currencies_in_text("Spolu: 12,00 €") == {"EUR"}
    assert currencies_in_text("unitPriceEUR,totalEUR") == {"EUR"}
    assert "USD" in currencies_in_text("Total $5.00")
    assert currencies_in_text("Spolu 120 Kč") == {"CZK"}
    # "EUROPE" or a lowercase word is not a currency mention.
    assert currencies_in_text("EUROPE and the euro area") == set()


@pytest.mark.parametrize(
    ("printed", "evidence", "supported"),
    [
        ("1.234,50", "Spolu 1.234,50 EUR", True),
        ("234,50", "Spolu 1.234,50 EUR", False),
        ("12,50", "12,505", False),
        ("1.3.2026", "zo dňa 11.3.2026", False),
        ("1.3.2026", "zo dňa 1.3.2026.", True),
        ("48 600,00", "EUR 48 600,00", True),
        ("ACME s.r.o.", "Dodávateľ: acme  s.r.o.", True),
    ],
)
def test_printed_value_must_not_be_part_of_a_longer_number(printed, evidence, supported):
    assert printed_text_supported(printed, [evidence]) is supported
