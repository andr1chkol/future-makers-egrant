import io
import json
import subprocess
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest
from app.documents.normalization import MEDIA_TYPES, declared_media_type, normalize
from app.documents.ocr import configured_ocr, ocr_configured
from app.documents.parsing import parse_document
from app.documents.settings import DocumentSettings
from app.platform.errors import DomainError
from openpyxl import Workbook
from PIL import Image


def test_text_pdf_provenance_and_stable_ids(text_pdf):
    document_id = uuid4()
    result = parse_document(text_pdf, "application/pdf", document_id)
    assert result.page_count == 2
    assert [(unit.text, unit.page, unit.sheet, unit.cell) for unit in result.units] == [
        ("First supporting page", 1, None, None),
        ("Second supporting page", 2, None, None),
    ]
    assert result.units == parse_document(text_pdf, "application/pdf", document_id).units
    assert result.units[0].id != parse_document(text_pdf, "application/pdf", uuid4()).units[0].id


def test_scanned_pdf_calls_fake_ocr_in_page_order(scanned_pdf):
    images = []

    def fake_ocr(image, remaining):
        assert image.startswith(b"\x89PNG") and 0 < remaining <= 40
        images.append(image)
        return f"Skenovaná strana {len(images)}"

    result = normalize(scanned_pdf, "application/pdf", uuid4(), DocumentSettings(), ocr=fake_ocr)
    assert [(unit.text, unit.page) for unit in result.units] == [
        ("Skenovaná strana 1", 1),
        ("Skenovaná strana 2", 2),
    ]
    assert len(images) == 2


@pytest.mark.parametrize("media_type", ["image/png", "image/jpeg"])
def test_image_fake_ocr(media_type):
    output = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(
        output, format="PNG" if media_type == "image/png" else "JPEG"
    )
    result = normalize(
        output.getvalue(), media_type, uuid4(), DocumentSettings(), ocr=lambda *_: "Pôvodný text"
    )
    assert result.page_count == 1
    assert result.units[0].text == "Pôvodný text"
    assert result.units[0].page == 1 and result.units[0].cell is None


def workbook_bytes():
    workbook = Workbook()
    workbook.active.title = "Rozpočet"
    workbook.active.append(["Položka", "Suma", "=1+1"])
    workbook.active.append(["Materiál", 12.5, None])
    workbook.create_sheet("Notes")["B4"] = "Original location"
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_xlsx_coordinates_and_unavailable_formula():
    result = parse_document(workbook_bytes(), MEDIA_TYPES[".xlsx"], uuid4())
    assert [(unit.sheet, unit.cell, unit.text, unit.page) for unit in result.units] == [
        ("Rozpočet", "A1", "Položka", None),
        ("Rozpočet", "B1", "Suma", None),
        ("Rozpočet", "A2", "Materiál", None),
        ("Rozpočet", "B2", "12.5", None),
        ("Notes", "B4", "Original location", None),
    ]
    assert [warning.code for warning in result.warnings] == ["FORMULA_VALUE_UNAVAILABLE"]


def test_xlsx_reads_cached_formula_without_execution():
    content = workbook_bytes()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(content)) as original, zipfile.ZipFile(output, "w") as updated:
        for member in original.infolist():
            data = original.read(member)
            if member.filename == "xl/worksheets/sheet1.xml":
                data = data.replace(b"<f>1+1</f><v/>", b"<f>1+1</f><v>2</v>")
                data = data.replace(b"<f>1+1</f><v />", b"<f>1+1</f><v>2</v>")
                data = data.replace(b"<f>1+1</f><v></v>", b"<f>1+1</f><v>2</v>")
            updated.writestr(member, data)
    result = parse_document(output.getvalue(), MEDIA_TYPES[".xlsx"], uuid4())
    assert next(unit.text for unit in result.units if unit.cell == "C1") == "2"
    assert not result.warnings


def test_csv_blank_rows_preserve_cell_positions(csv_content):
    result = parse_document(csv_content, "text/csv", uuid4())
    assert [(unit.id, unit.sheet, unit.cell, unit.text) for unit in result.units] == [
        ("row-1", "CSV", "A1:B1", "name,amount"),
        ("row-2", "CSV", "A2:B2", "Žiadosť,12.50"),
        ("row-4", "CSV", "A4:B4", "Druhý,20.00"),
    ]
    assert all(unit.page is None for unit in result.units)


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16"])
def test_csv_encodings_and_quoted_multiline(encoding):
    result = parse_document(
        'name;value\n"Two\nlines";Žiadosť\n'.encode(encoding), "text/csv", uuid4()
    )
    assert result.units[1].cell == "A2:B2"
    assert result.units[1].text == '"Two\nlines";Žiadosť'


def test_synthetic_csv_matches_extraction_fixture_sources():
    root = Path(__file__).resolve().parents[2]
    reference = json.loads(
        (root / "contracts/examples/normalized-document.json").read_text(encoding="utf-8")
    )
    content = (root / "contracts/examples/synthetic-invoice.csv").read_bytes()
    document_id = uuid4()
    result = parse_document(content, "text/csv", document_id)
    # Extraction's recorded-provider fingerprint uses unit IDs and original text, not sheet aliases.
    assert [[unit.id, unit.text] for unit in result.units] == [
        [unit["id"], unit["text"]] for unit in reference["units"]
    ]
    assert [(unit.page, unit.cell) for unit in result.units] == [
        (unit["page"], unit["cell"]) for unit in reference["units"]
    ]
    assert result.units == parse_document(content, "text/csv", document_id).units
    assert {unit.sheet for unit in result.units} == {"CSV"}


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_csv_preserves_original_quoting_and_record_boundaries(newline):
    row = f'"first{newline}second","quoted ""value"""'
    content = f"name,value{newline}{row}{newline}".encode()
    result = parse_document(content, "text/csv", uuid4())
    assert [(unit.id, unit.cell, unit.text) for unit in result.units] == [
        ("row-1", "A1:B1", "name,value"),
        ("row-2", "A2:B2", row),
    ]


@pytest.mark.parametrize(
    ("content", "media", "code"),
    [
        (b"%PDF-broken", "application/pdf", "CORRUPT_FILE"),
        (b"\x89PNG\r\n\x1a\ninvalid", "image/png", "CORRUPT_FILE"),
        (b"PK\x03\x04invalid", MEDIA_TYPES[".xlsx"], "CORRUPT_FILE"),
        (b"a,b\n1,2,3", "text/csv", "CSV_MALFORMED"),
        (b'a,b\n"unfinished,2', "text/csv", "CSV_MALFORMED"),
        (b"a,b\n\xff,2", "text/csv", "CSV_ENCODING"),
        (b"\x00binary", "text/csv", "UNSUPPORTED_CONTENT"),
        (b"<html>hello</html>", "text/csv", "MIME_MISMATCH"),
        (b"", "text/csv", "EMPTY_FILE"),
        (b"\n\n", "text/csv", "EMPTY_DOCUMENT"),
    ],
)
def test_invalid_content_fails_safely(content, media, code):
    with pytest.raises(DomainError) as caught:
        parse_document(content, media, uuid4())
    assert caught.value.code == code


@pytest.mark.parametrize(
    ("filename", "media", "content"),
    [
        ("file.pdf", "application/pdf", b"not a PDF"),
        ("file.csv", "text/csv", b"%PDF-1.7"),
        ("file.png", "image/jpeg", b"\x89PNG\r\n\x1a\n"),
        ("file.exe", "application/octet-stream", b"MZ"),
    ],
)
def test_declared_type_and_signature_spoofing(filename, media, content):
    with pytest.raises(DomainError):
        declared_media_type(filename, media, content)


@pytest.mark.parametrize(
    ("field", "value", "code", "format"),
    [
        ("max_bytes", 5, "UPLOAD_TOO_LARGE", "csv"),
        ("max_rows", 1, "ROW_LIMIT", "csv"),
        ("max_columns", 1, "CELL_LIMIT", "csv"),
        ("max_cells", 2, "CELL_LIMIT", "csv"),
        ("max_pages", 1, "PAGE_LIMIT", "pdf"),
        ("max_pixels", 10, "IMAGE_LIMIT", "image"),
        ("max_rows", 1, "ROW_LIMIT", "xlsx"),
        ("max_uncompressed_bytes", 100, "DECOMPRESSION_LIMIT", "xlsx"),
        ("max_compression_ratio", 1, "DECOMPRESSION_LIMIT", "xlsx"),
        ("max_zip_files", 2, "DECOMPRESSION_LIMIT", "xlsx"),
        ("max_sheets", 1, "SHEET_LIMIT", "xlsx"),
    ],
)
def test_format_limits(field, value, code, format, text_pdf, png_content, csv_content):
    content, media = {
        "csv": (csv_content, "text/csv"),
        "pdf": (text_pdf, "application/pdf"),
        "image": (png_content, "image/png"),
        "xlsx": (workbook_bytes(), MEDIA_TYPES[".xlsx"]),
    }[format]
    with pytest.raises(DomainError) as caught:
        normalize(content, media, uuid4(), DocumentSettings(**{field: value}))
    assert caught.value.code == code


def test_empty_ocr_and_unconfigured_live_adapter(png_content, monkeypatch):
    with pytest.raises(DomainError, match="OCR_EMPTY"):
        normalize(png_content, "image/png", uuid4(), DocumentSettings(), ocr=lambda *_: " \n")
    monkeypatch.setenv("APP_MODE", "live")
    with pytest.raises(DomainError, match="OCR_UNAVAILABLE"):
        parse_document(png_content, "image/png", uuid4())
    assert not ocr_configured(DocumentSettings())


@pytest.mark.parametrize(
    ("failure", "code"),
    [
        (subprocess.TimeoutExpired("ocr", 1), "OCR_TIMEOUT"),
        (OSError("secret-provider-key"), "OCR_FAILED"),
    ],
)
def test_ocr_errors_are_sanitized(failure, code, tmp_path, monkeypatch):
    executable = tmp_path / "tesseract"
    executable.touch()
    settings = DocumentSettings(ocr_provider="tesseract", ocr_executable=executable)

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr("app.documents.ocr.subprocess.run", fail)
    with pytest.raises(DomainError) as caught:
        configured_ocr(settings)(b"private", 10)
    assert caught.value.code == code
    assert "secret" not in caught.value.message


def test_parser_timeout_is_explicit(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("parser", 1)

    monkeypatch.setattr("app.documents.parsing.subprocess.run", timeout)
    with pytest.raises(DomainError, match="PROCESSING_TIMEOUT"):
        parse_document(b"name,value", "text/csv", uuid4())


@pytest.mark.parametrize("attack", ["macro", "entity"])
def test_spreadsheet_code_and_xml_entities_are_rejected(attack):
    output = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(workbook_bytes())) as original,
        zipfile.ZipFile(output, "w") as updated,
    ):
        for member in original.infolist():
            updated.writestr(member, original.read(member))
        if attack == "macro":
            updated.writestr("xl/vbaProject.bin", b"must never execute")
        else:
            updated.writestr(
                "extra.xml", b'<!DOCTYPE data [<!ENTITY value "private">]><data>&value;</data>'
            )
    with pytest.raises(DomainError) as caught:
        parse_document(output.getvalue(), MEDIA_TYPES[".xlsx"], uuid4())
    assert caught.value.code == ("UNSUPPORTED_CONTENT" if attack == "macro" else "CORRUPT_FILE")


def test_sparse_workbook_cannot_hide_rows_with_false_dimensions():
    output = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(workbook_bytes())) as original,
        zipfile.ZipFile(output, "w") as updated,
    ):
        for member in original.infolist():
            data = original.read(member)
            if member.filename == "xl/worksheets/sheet2.xml":
                data = (
                    data.replace(b"B4:B4", b"A1:A1")
                    .replace(b'r="4"', b'r="10001"')
                    .replace(b"B4", b"B10001")
                )
            updated.writestr(member, data)
    with pytest.raises(DomainError, match="ROW_LIMIT"):
        normalize(output.getvalue(), MEDIA_TYPES[".xlsx"], uuid4(), DocumentSettings())
