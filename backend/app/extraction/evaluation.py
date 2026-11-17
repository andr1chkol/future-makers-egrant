"""Repeatable evaluation of extraction output against manually checked expectations.

    cd backend
    uv run python -m app.extraction.evaluation ../tests/extraction/evaluation/heldout
    uv run python -m app.extraction.evaluation ../tests/extraction/evaluation/heldout --live

Without --live every case is run through parsing, normalization and validation
using the reply recorded in the case file. That measures this module's handling
of a given reply, not the accuracy of any model. --live sends each case document
to the configured OpenAI model and is a paid external call.

Counts are per value slot: scalar fields plus every cell of every expected or
extracted row. Rows are compared by position because document order is part of
the contract for line items.
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.extraction.assembly import assemble_extraction
from app.extraction.providers import OpenAIProvider, ProviderError
from app.extraction.schema import ProviderOutputError, parse_provider_output
from app.platform.contracts import ExtractedField, NormalizedDocument, Profile
from app.platform.settings import get_settings


@dataclass
class Score:
    cases: int = 0
    failed_cases: int = 0
    expected_values: int = 0
    correct: int = 0
    missing: int = 0
    incorrect: int = 0
    invented: int = 0
    correctly_absent: int = 0
    flagged_for_review: int = 0
    expected_rows: int = 0
    extracted_rows: int = 0
    failures: list[str] = field(default_factory=list)

    def compare(self, expected, extracted: ExtractedField | None) -> None:
        actual = None if extracted is None else extracted.model_dump(mode="json")["value"]
        if extracted is not None and extracted.status == "needs_review":
            self.flagged_for_review += 1
        if expected is not None:
            self.expected_values += 1
        if expected is None and actual is None:
            self.correctly_absent += 1
        elif expected is None:
            self.invented += 1
        elif actual is None:
            self.missing += 1
        elif actual == expected:
            self.correct += 1
        else:
            self.incorrect += 1


def load_case(path: Path) -> dict:
    case = json.loads(path.read_text())
    profiles = path.parent.parent / "profiles"
    case["profile"] = Profile.model_validate_json(
        (profiles / f"{case['profile']}.json").read_text()
    )
    case["document"] = NormalizedDocument.model_validate(case["document"])
    return case


def evaluate_case(case: dict, score: Score, provider: OpenAIProvider | None) -> None:
    profile, document, expected = case["profile"], case["document"], case["expected"]
    score.cases += 1
    try:
        if provider is None:
            reply = json.dumps(case["recordedReply"], ensure_ascii=False)
        else:
            reply = provider.extract(profile, case["options"], document)
        raw = parse_provider_output(reply, profile)
    except (ProviderError, ProviderOutputError) as error:
        score.failed_cases += 1
        score.failures.append(f"{case['name']}: {getattr(error, 'code', 'AI_OUTPUT_INVALID')}")
        raw = None
    result = assemble_extraction(raw, profile, document, case["options"]) if raw else None

    fields = {item.key: item for item in result.fields} if result else {}
    for spec in profile.scalar_fields:
        score.compare(expected["fields"][spec.key], fields.get(spec.key))
    tables = {table.key: table for table in result.tables} if result else {}
    for spec in profile.table_fields:
        expected_rows = expected["tables"][spec.key]
        rows = tables[spec.key].rows if spec.key in tables else []
        score.expected_rows += len(expected_rows)
        score.extracted_rows += len(rows)
        for index in range(max(len(expected_rows), len(rows))):
            expected_row = expected_rows[index] if index < len(expected_rows) else {}
            cells = {cell.key: cell for cell in rows[index].cells} if index < len(rows) else {}
            for column in spec.columns:
                score.compare(expected_row.get(column.key), cells.get(column.key))


def evaluate(directory: Path, live: bool) -> Score:
    provider = None
    if live:
        provider = OpenAIProvider.from_settings(get_settings())
        if provider is None:
            raise SystemExit("--live requires OPENAI_API_KEY and OPENAI_MODEL")
    score = Score()
    for path in sorted(directory.glob("*.json")):
        evaluate_case(load_case(path), score, provider)
    return score


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cases", type=Path, help="Directory of case files, e.g. a held-out split")
    parser.add_argument("--live", action="store_true", help="Call the configured AI provider")
    arguments = parser.parse_args(argv)
    score = evaluate(arguments.cases, arguments.live)
    report = {"provider": "live" if arguments.live else "recorded", "split": str(arguments.cases)}
    json.dump({**report, **asdict(score)}, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
