import json
from pathlib import Path

from app.extraction.evaluation import evaluate, main
from extraction_support import EVALUATION


def test_splits_do_not_share_documents():
    def documents(split):
        return {
            json.loads(path.read_text())["document"]["documentId"]
            for path in (EVALUATION / split).glob("*.json")
        }

    tuning, heldout = documents("tuning"), documents("heldout")
    assert tuning and heldout
    assert not tuning & heldout


def test_recorded_heldout_evaluation_counts_each_kind_of_error():
    score = evaluate(EVALUATION / "heldout", live=False)
    # The recorded held-out replies contain, by construction: swapped supplier and
    # buyer, a wrong contract type, an injected total (4 incorrect); an invented due
    # date (1 invented); and a dropped bank transaction (3 missing cells).
    assert (score.cases, score.failed_cases) == (4, 0)
    assert score.expected_values == 51
    assert (score.correct, score.incorrect, score.invented, score.missing) == (44, 4, 1, 3)
    assert (score.expected_rows, score.extracted_rows) == (9, 8)
    # Invented due date, injected total and the unbalanced statement are flagged.
    assert score.flagged_for_review == 3


def test_evaluation_is_repeatable_and_reports_json(capsys):
    main([str(EVALUATION / "tuning")])
    first = json.loads(capsys.readouterr().out)
    main([str(EVALUATION / "tuning")])
    assert json.loads(capsys.readouterr().out) == first
    assert first["provider"] == "recorded"
    assert first["correct"] == first["expected_values"] == 32


def test_invalid_reply_counts_every_expected_value_as_missing(tmp_path: Path):
    split = tmp_path / "split"
    split.mkdir()
    (tmp_path / "profiles").symlink_to(EVALUATION / "profiles")
    case = json.loads((EVALUATION / "tuning" / "receipt-card.json").read_text())
    case["recordedReply"] = {"fields": {}}
    (split / "broken.json").write_text(json.dumps(case))
    score = evaluate(split, live=False)
    assert score.failed_cases == 1
    assert score.missing == score.expected_values
    assert score.failures == ["receipt-card: AI_OUTPUT_INVALID"]
