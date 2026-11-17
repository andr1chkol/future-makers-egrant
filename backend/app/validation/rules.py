"""Cross-field domain checks on an assembled extraction.

Profiles carry no semantic roles in contract v1, so arithmetic checks recognize
conventional field keys. A profile whose keys use other names still extracts
normally; it only skips these checks. Mismatches are reported and flagged for
review. Extracted values are never rewritten to make the numbers agree, and no
calculated value is stored as if it had been read from the document.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.platform.contracts import ExtractedField, ExtractedTable, Money, Warning
from app.validation.values import decimal_places

QUANTITY_KEYS = {"quantity", "qty"}
UNIT_PRICE_KEYS = {"unit_price", "unit_price_net", "price_per_unit"}
# Ordered: a table with both "line_total" and "total" columns uses the more specific one.
LINE_TOTAL_KEYS = ("line_total", "line_amount", "amount", "total")
NET_KEYS = {"net_total", "total_net", "subtotal", "net_amount", "total_without_vat"}
TAX_KEYS = {"tax_total", "vat_total", "tax_amount", "vat_amount", "tax", "vat"}
GROSS_KEYS = {"total", "gross_total", "total_gross", "total_amount", "total_with_vat"}
OPENING_BALANCE_KEYS = {"opening_balance"}
CLOSING_BALANCE_KEYS = {"closing_balance"}


@dataclass
class Amount:
    field: ExtractedField
    value: Decimal
    currency: str | None
    places: int

    @property
    def rounding(self) -> Decimal:
        """Half of the last printed digit: the most a correctly rounded figure can be off."""
        return Decimal(1).scaleb(-self.places) / 2


def amount_of(field: ExtractedField | None) -> Amount | None:
    if field is None or field.value is None:
        return None
    if isinstance(field.value, Money):
        return Amount(
            field,
            Decimal(field.value.amount),
            field.value.currency,
            decimal_places(field.value.amount),
        )
    if field.type == "decimal":
        return Amount(field, Decimal(field.value), None, decimal_places(field.value))
    return None


def find(fields: list[ExtractedField], keys: set[str]) -> ExtractedField | None:
    return next((field for field in fields if field.key in keys), None)


def same_currency(*amounts: Amount) -> bool:
    currencies = {amount.currency for amount in amounts if amount.currency is not None}
    return len(currencies) <= 1


def flag(*amounts: Amount) -> None:
    for amount in amounts:
        amount.field.status = "needs_review"


def check_extraction_rules(
    fields: list[ExtractedField], tables: list[ExtractedTable]
) -> list[Warning]:
    """Return warnings for inconsistent figures and flag the fields involved."""
    warnings = [*check_currency_consistency(fields, tables)]
    line_tables: list[tuple[ExtractedTable, str]] = []
    for table in tables:
        if not table.rows:
            continue
        column_keys = {cell.key for cell in table.rows[0].cells}
        line_key = next((key for key in LINE_TOTAL_KEYS if key in column_keys), None)
        if line_key is None:
            continue
        line_tables.append((table, line_key))
        warnings.extend(check_line_totals(table, column_keys, line_key))
    # Summing is only meaningful when a single table holds the document's lines.
    if len(line_tables) == 1:
        table, line_key = line_tables[0]
        warnings.extend(check_document_totals(fields, table, line_key))
    warnings.extend(check_tax_total(fields))
    return warnings


def check_currency_consistency(
    fields: list[ExtractedField], tables: list[ExtractedTable]
) -> list[Warning]:
    cells = [cell for table in tables for row in table.rows for cell in row.cells]
    currencies = {
        item.value.currency for item in [*fields, *cells] if isinstance(item.value, Money)
    }
    if len(currencies) <= 1:
        return []
    # Several currencies can be legitimate (foreign transactions), so this only warns.
    return [
        Warning(
            code="CURRENCY_INCONSISTENT",
            message="The document's amounts use more than one currency",
        )
    ]


def check_line_totals(table: ExtractedTable, column_keys: set[str], line_key: str) -> list[Warning]:
    quantity_key = next(iter(column_keys & QUANTITY_KEYS), None)
    price_key = next(iter(column_keys & UNIT_PRICE_KEYS), None)
    if quantity_key is None or price_key is None:
        return []
    warnings = []
    for row in table.rows:
        cells = {cell.key: cell for cell in row.cells}
        quantity = amount_of(cells[quantity_key])
        price = amount_of(cells[price_key])
        line = amount_of(cells[line_key])
        if not (quantity and price and line) or not same_currency(price, line):
            continue
        # A unit price rounded to its printed precision can be off by half a digit
        # for every unit; the printed line total adds its own rounding.
        tolerance = price.rounding * abs(quantity.value) + line.rounding
        if abs(quantity.value * price.value - line.value) > tolerance:
            flag(line)
            warnings.append(
                Warning(
                    code="LINE_TOTAL_MISMATCH",
                    message="Line total differs from quantity × unit price beyond rounding",
                    field_key=line_key,
                    table_key=table.key,
                    row_id=row.row_id,
                )
            )
    return warnings


def check_document_totals(
    fields: list[ExtractedField], table: ExtractedTable, line_key: str
) -> list[Warning]:
    lines = [amount_of(cell) for row in table.rows for cell in row.cells if cell.key == line_key]
    if not lines or any(line is None for line in lines):
        return []
    line_sum = sum((line.value for line in lines), Decimal(0))
    # Each line may have been rounded independently before the document summed them.
    lines_rounding = sum((line.rounding for line in lines), Decimal(0))

    opening = amount_of(find(fields, OPENING_BALANCE_KEYS))
    closing = amount_of(find(fields, CLOSING_BALANCE_KEYS))
    if opening and closing:
        if not same_currency(opening, closing, *lines):
            return []
        expected = opening.value + line_sum
        if abs(expected - closing.value) > lines_rounding + opening.rounding + closing.rounding:
            flag(closing)
            return [
                Warning(
                    code="BALANCE_MISMATCH",
                    message="Opening balance plus transactions differs from the closing balance",
                    field_key=closing.field.key,
                )
            ]
        return []

    net = amount_of(find(fields, NET_KEYS))
    tax = amount_of(find(fields, TAX_KEYS))
    gross = amount_of(find(fields, GROSS_KEYS))
    # Lines are compared to the net total, or to the gross total when no tax amount
    # was extracted. If tax exists but was missed, the resulting warning is still true:
    # the lines do not add up to the total, and the missing tax is reported separately.
    target = net or (gross if tax is None else None)
    if target is None or not same_currency(target, *lines):
        return []
    if abs(line_sum - target.value) > lines_rounding + target.rounding:
        flag(target)
        return [
            Warning(
                code="DOCUMENT_TOTAL_MISMATCH",
                message="The sum of table line totals differs from the document total",
                field_key=target.field.key,
                table_key=table.key,
            )
        ]
    return []


def check_tax_total(fields: list[ExtractedField]) -> list[Warning]:
    net = amount_of(find(fields, NET_KEYS))
    tax = amount_of(find(fields, TAX_KEYS))
    gross = amount_of(find(fields, GROSS_KEYS))
    if not (net and tax and gross) or not same_currency(net, tax, gross):
        return []
    if abs(net.value + tax.value - gross.value) > net.rounding + tax.rounding + gross.rounding:
        flag(gross)
        return [
            Warning(
                code="TAX_TOTAL_MISMATCH",
                message="Net amount plus tax differs from the gross total",
                field_key=gross.field.key,
            )
        ]
    return []
