"""Shared test data and doubles for extraction tests (imported by module name)."""

import json
from pathlib import Path

from app.platform.contracts import FormDefinition, NormalizedDocument, Profile

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "contracts/examples"
EVALUATION = Path(__file__).parent / "evaluation"


def example_profile() -> Profile:
    return Profile.model_validate_json((EXAMPLES / "profile.json").read_text())


def example_form() -> FormDefinition:
    return FormDefinition.model_validate_json((EXAMPLES / "form.json").read_text())


def example_document() -> NormalizedDocument:
    return NormalizedDocument.model_validate_json(
        (EXAMPLES / "normalized-document.json").read_text()
    )


def evaluation_profile(name: str) -> Profile:
    return Profile.model_validate_json((EVALUATION / "profiles" / f"{name}.json").read_text())


def evaluation_case(split: str, name: str) -> dict:
    return json.loads((EVALUATION / split / f"{name}.json").read_text())


def value(printed, unit_id=None, quote=None):
    """A provider reply entry citing one unit; the quote defaults to the printed value."""
    evidence = [] if unit_id is None else [{"unitId": unit_id, "quote": quote or printed}]
    return {"value": printed, "evidence": evidence}


def money(amount, currency, unit_id, quote=None):
    return {
        "value": {"amount": amount, "currency": currency},
        "evidence": [{"unitId": unit_id, "quote": quote or amount}],
    }


def reply_for(profile: Profile, fields: dict | None = None, tables: dict | None = None) -> dict:
    """Build a schema-complete reply; anything not given is an honest null."""
    fields = fields or {}
    tables = tables or {}
    return {
        "fields": {
            spec.key: fields.get(spec.key, {"value": None, "evidence": []})
            for spec in profile.scalar_fields
        },
        "tables": {
            table.key: {
                "rows": [
                    {
                        "cells": {
                            column.key: cells.get(column.key, {"value": None, "evidence": []})
                            for column in table.columns
                        }
                    }
                    for cells in tables.get(table.key, [])
                ]
            }
            for table in profile.table_fields
        },
    }


class ScriptedProvider:
    """Deterministic provider: replays the given outcomes, repeating the last one."""

    def __init__(self, *outcomes, mode="fixture"):
        self.outcomes = list(outcomes)
        self.mode = mode
        self.calls = 0

    def extract(self, profile, options, document):
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        if callable(outcome):
            outcome = outcome()
        return outcome if isinstance(outcome, str) else json.dumps(outcome, ensure_ascii=False)
