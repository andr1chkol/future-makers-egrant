"""Opt-in cross-module smoke check using the real CSV parser and explicit extraction fixture."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

import app
from app.documents.parsing import parse_document
from app.platform.contracts import Extraction, NormalizedDocument, Profile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extraction-app-path", type=Path)
    arguments = parser.parse_args()
    if arguments.extraction_app_path:
        app.__path__.append(str(arguments.extraction_app_path.resolve()))

    from app.extraction.assembly import assemble_extraction
    from app.extraction.providers import FixtureProvider
    from app.extraction.schema import parse_provider_output

    root = Path(__file__).resolve().parents[2]
    examples = root / "contracts/examples"
    profile = Profile.model_validate_json((examples / "profile.json").read_text(encoding="utf-8"))
    expected = Extraction.model_validate_json(
        (examples / "extraction.json").read_text(encoding="utf-8")
    )
    document_id = uuid4()
    parsed = parse_document(
        (examples / "synthetic-invoice.csv").read_bytes(), "text/csv", document_id
    )
    document = NormalizedDocument(document_id=document_id, units=parsed.units)
    raw = FixtureProvider().extract(profile, {}, document)
    assembled = assemble_extraction(parse_provider_output(raw, profile), profile, document, {})
    assert [(field.key, field.value) for field in assembled.fields] == [
        (field.key, field.value) for field in expected.fields
    ]
    assert [
        [[(cell.key, cell.value) for cell in row.cells] for row in table.rows]
        for table in assembled.tables
    ] == [
        [[(cell.key, cell.value) for cell in row.cells] for row in table.rows]
        for table in expected.tables
    ]
    units = {unit.id: unit for unit in document.units}
    values = assembled.fields + [
        cell for table in assembled.tables for row in table.rows for cell in row.cells
    ]
    for value in values:
        for source in value.sources:
            assert source.document_id == document_id
            assert source.unit_id in units and source.quote in units[source.unit_id].text
            assert source.sheet == "CSV" and source.cell == units[source.unit_id].cell
    print(
        json.dumps(
            {
                "status": "PASSED",
                "providerMode": "fixture",
                "sourceUnitCount": len(units),
                "fieldCount": len(assembled.fields),
                "tableRowCount": sum(len(table.rows) for table in assembled.tables),
            }
        )
    )


if __name__ == "__main__":
    main()
