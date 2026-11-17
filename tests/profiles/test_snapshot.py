import json
from pathlib import Path
from unittest.mock import Mock

from app.profiles.models import ImportedForm
from app.profiles.service import get_form, list_forms


def test_form_reads_return_detached_unknown_settings():
    source = json.loads(Path("contracts/examples/form.json").read_text())
    record = ImportedForm(id=source["id"], name=source["name"], snapshot=source)
    session = Mock()
    session.get.return_value = record
    session.scalar.return_value = 1
    session.scalars.return_value = [record]
    original = get_form(session, record.id)
    original.original_json["unknownConfiguration"]["preserved"] = False
    assert get_form(session, record.id).original_json["unknownConfiguration"]["preserved"] is True
    listing = list_forms(session)
    listing.data[0].original_json["unknownConfiguration"]["preserved"] = False
    assert get_form(session, record.id).original_json["unknownConfiguration"]["preserved"] is True
