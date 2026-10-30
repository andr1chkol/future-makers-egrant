import csv
import io
import math
import time
import warnings
import zipfile
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from uuid import UUID, uuid5

from app.documents.ocr import OCR, configured_ocr
from app.documents.settings import DocumentSettings
from app.platform.contracts import SourceUnit, Warning
from app.platform.errors import DomainError

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
}


@dataclass
class Normalization:
    units: list[SourceUnit] = field(default_factory=list)
    warnings: list[Warning] = field(default_factory=list)
    page_count: int | None = None


def reject(code: str, message: str, status: int = 422):
    raise DomainError(code, status, message)


def declared_media_type(filename: str, declared: str | None, content: bytes) -> str:
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    expected = MEDIA_TYPES.get(suffix)
    if expected is None:
        reject("UNSUPPORTED_CONTENT", "Supported formats are PDF, JPEG, PNG, XLSX and CSV")
    if declared != expected:
        reject("MIME_MISMATCH", "Declared type does not match the supported file extension")
    signatures = {
        "application/pdf": content.startswith(b"%PDF-"),
        "image/jpeg": content.startswith(b"\xff\xd8\xff"),
        "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        MEDIA_TYPES[".xlsx"]: content.startswith(b"PK\x03\x04"),
        "text/csv": not content.startswith((b"%PDF-", b"PK", b"\xff\xd8", b"\x89PNG")),
    }
    if not signatures[expected]:
        reject("MIME_MISMATCH", "File content does not match its declared type")
    return expected


def normalize(
    content: bytes,
    media_type: str,
    document_id: UUID,
    settings: DocumentSettings,
    *,
    validation_only: bool = False,
    ocr: OCR | None = None,
) -> Normalization:
    result = Normalization()
    started = time.monotonic()
    character_count = 0
    recognize = ocr or configured_ocr(settings)

    def add(text: str, *, page=None, sheet=None, cell=None, unit_id=None):
        nonlocal character_count
        character_count += len(text)
        if character_count > settings.max_text_chars or len(result.units) >= settings.max_cells:
            reject("SOURCE_LIMIT", "Normalized content exceeds the configured limit", 413)
        location = f"page:{page}" if page is not None else f"sheet:{sheet}:cell:{cell}"
        result.units.append(
            SourceUnit(
                id=unit_id or str(uuid5(document_id, location)),
                text=text,
                page=page,
                sheet=sheet,
                cell=cell,
            )
        )

    def read_ocr(image: bytes) -> str:
        remaining = settings.processing_seconds - (time.monotonic() - started)
        if remaining <= 0:
            reject("PROCESSING_TIMEOUT", "Document processing exceeded its time limit", 502)
        text = recognize(image, remaining).strip()
        if not text:
            reject("OCR_EMPTY", "OCR returned no usable text")
        return text

    if not content:
        reject("EMPTY_FILE", "File is empty")
    if len(content) > settings.max_bytes:
        reject("UPLOAD_TOO_LARGE", "File exceeds the configured size limit", 413)
    if media_type == "application/pdf":
        import pypdfium2 as pdfium

        with pdfium.PdfDocument(content) as pdf:
            result.page_count = len(pdf)
            if not len(pdf):
                reject("EMPTY_DOCUMENT", "PDF has no pages")
            if len(pdf) > settings.max_pages:
                reject("PAGE_LIMIT", "PDF exceeds the configured page limit", 413)
            if not validation_only:
                for index in range(len(pdf)):
                    with closing(pdf[index]) as page:
                        with closing(page.get_textpage()) as text_page:
                            if text_page.count_chars() > settings.max_text_chars:
                                reject("SOURCE_LIMIT", "PDF text exceeds the configured limit", 413)
                            text = text_page.get_text_range().strip()
                        if not any(character.isalnum() for character in text):
                            width, height = page.get_size()
                            if not all(
                                math.isfinite(value) and value > 0 for value in (width, height)
                            ):
                                reject("CORRUPT_FILE", "Invalid PDF page dimensions")
                            scale = min(2.0, math.sqrt(settings.max_pixels / (width * height)))
                            bitmap = page.render(scale=scale)
                            try:
                                image = bitmap.to_pil()
                                buffer = io.BytesIO()
                                image.save(buffer, format="PNG")
                                text = read_ocr(buffer.getvalue())
                            finally:
                                bitmap.close()
                        add(text, page=index + 1)
    elif media_type in {"image/jpeg", "image/png"}:
        from PIL import Image, ImageOps

        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                expected = "PNG" if media_type == "image/png" else "JPEG"
                if image.format != expected:
                    reject("MIME_MISMATCH", "Decoded image type does not match its declared type")
                if image.width * image.height > settings.max_pixels:
                    reject("IMAGE_LIMIT", "Image exceeds the configured pixel limit", 413)
                if getattr(image, "n_frames", 1) != 1:
                    reject("UNSUPPORTED_CONTENT", "Animated images are not supported")
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                image.load()
                result.page_count = 1
                if not validation_only:
                    buffer = io.BytesIO()
                    ImageOps.exif_transpose(image).convert("RGB").save(buffer, format="PNG")
                    add(read_ocr(buffer.getvalue()), page=1)
    elif media_type == "text/csv":
        csv.field_size_limit(settings.max_text_chars)
        try:
            encoding = "utf-16" if content.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
            text = content.decode(encoding)
        except UnicodeError:
            reject("CSV_ENCODING", "CSV must use UTF-8 or BOM-marked UTF-16")
        if any(ord(character) < 32 and character not in "\r\n\t" for character in text):
            reject("UNSUPPORTED_CONTENT", "CSV contains binary control characters")
        if text.lstrip().lower().startswith(("<html", "<!doctype", "<?xml", "<svg")):
            reject("MIME_MISMATCH", "Markup is not a supported CSV document")
        try:
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        width = None
        cells = 0
        from openpyxl.utils import get_column_letter

        stream = io.StringIO(text, newline="")
        record_start = 0
        try:
            for row_number, row in enumerate(csv.reader(stream, dialect, strict=True), 1):
                record_end = stream.tell()
                row_text = text[record_start:record_end].removesuffix("\n").removesuffix("\r")
                record_start = record_end
                if row_number > settings.max_rows:
                    reject("ROW_LIMIT", "CSV exceeds the configured row limit", 413)
                if not row or all(not value.strip() for value in row):
                    continue
                width = width or len(row)
                if len(row) != width:
                    reject("CSV_MALFORMED", "CSV rows have inconsistent column counts")
                cells += len(row)
                if len(row) > settings.max_columns or cells > settings.max_cells:
                    reject("CELL_LIMIT", "CSV exceeds the configured cell limit", 413)
                # A CSV has logical records, not named workbook sheets. Keep each original
                # record intact so quotes and extraction evidence survive normalization.
                add(
                    row_text,
                    sheet="CSV",
                    cell=f"A{row_number}:{get_column_letter(len(row))}{row_number}",
                    unit_id=f"row-{row_number}",
                )
        except csv.Error:
            reject("CSV_MALFORMED", "CSV quoting or field size is invalid")
    elif media_type == MEDIA_TYPES[".xlsx"]:
        _read_workbook(content, settings, result, add)
    else:
        reject("UNSUPPORTED_CONTENT", "Unsupported document format")
    if not validation_only and not result.units:
        reject("EMPTY_DOCUMENT", "Document contains no usable source values")
    return result


def _read_workbook(content, settings, result, add):
    from defusedxml.ElementTree import fromstring
    from openpyxl import load_workbook

    # Bound the archive before openpyxl allocates shared strings or worksheet objects.
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        members = archive.infolist()
        if len(members) > settings.max_zip_files:
            reject("DECOMPRESSION_LIMIT", "Spreadsheet archive has too many entries", 413)
        total = sum(member.file_size for member in members)
        if total > settings.max_uncompressed_bytes or any(
            member.file_size > max(1, member.compress_size) * settings.max_compression_ratio
            for member in members
        ):
            reject("DECOMPRESSION_LIMIT", "Spreadsheet archive exceeds decompression limits", 413)
        names = [member.filename for member in members]
        if len(names) != len(set(names)):
            reject("CORRUPT_FILE", "Spreadsheet contains duplicate archive entries")
        if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
            reject("MIME_MISMATCH", "Archive is not an XLSX workbook")
        for member in members:
            if member.flag_bits & 1 or "vbaproject" in member.filename.lower():
                reject("UNSUPPORTED_CONTENT", "Encrypted archives and macros are not supported")
            if member.filename.endswith((".xml", ".rels")):
                # Reject DTD/entity payloads, including in XML the workbook reader ignores.
                fromstring(archive.read(member))
    formulas = load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
    cached = None
    try:
        cached = load_workbook(
            io.BytesIO(content), read_only=True, data_only=True, keep_links=False
        )
        if len(formulas.worksheets) > settings.max_sheets:
            reject("SHEET_LIMIT", "Spreadsheet exceeds the configured sheet limit", 413)
        row_count = 0
        cell_count = 0
        missing_formula_count = 0
        for sheet, values in zip(formulas.worksheets, cached.worksheets, strict=True):
            if (sheet.max_row or 0) > settings.max_rows or (
                sheet.max_column or 0
            ) > settings.max_columns:
                reject("ROW_LIMIT", "Spreadsheet dimensions exceed the configured limits", 413)
            # Producer dimensions can under-report actual cells; read actual worksheet rows.
            sheet.reset_dimensions()
            values.reset_dimensions()
            for row, value_row in zip(sheet.rows, values.rows, strict=True):
                row_count += 1
                cell_count += len(row)
                if row_count > settings.max_rows:
                    reject("ROW_LIMIT", "Spreadsheet exceeds the configured row limit", 413)
                if len(row) > settings.max_columns or cell_count > settings.max_cells:
                    reject("CELL_LIMIT", "Spreadsheet exceeds the configured cell limit", 413)
                for cell, cached_cell in zip(row, value_row, strict=True):
                    value = cached_cell.value if cell.data_type == "f" else cell.value
                    if cell.data_type == "f" and value is None:
                        missing_formula_count += 1
                    if value is not None:
                        add(str(value), sheet=sheet.title, cell=cell.coordinate)
        if missing_formula_count:
            result.warnings.append(
                Warning(
                    code="FORMULA_VALUE_UNAVAILABLE",
                    message=(
                        f"{missing_formula_count} formula cells have no cached value; "
                        "formulas were not executed"
                    ),
                )
            )
    finally:
        formulas.close()
        if cached is not None:
            cached.close()
