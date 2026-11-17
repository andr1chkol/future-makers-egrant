import io
import json
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.documents import parse_worker


@pytest.mark.parametrize("platform", ["darwin", "win32"])
def test_non_linux_parser_accepts_csv_without_linux_address_space_limit(monkeypatch, platform):
    monkeypatch.setattr(parse_worker.logging, "disable", lambda _: None)
    output = io.StringIO()
    monkeypatch.setattr(
        parse_worker,
        "sys",
        SimpleNamespace(
            platform=platform,
            stdin=SimpleNamespace(buffer=io.BytesIO(b"name,value\nSource,12.50\n")),
            stdout=output,
            argv=["parse_worker", "text/csv", str(uuid4()), "normalize"],
        ),
    )
    # macOS rejects this Linux limit before the parser can return its safe JSON protocol.
    if platform == "darwin":

        def reject_limit(*args):
            raise ValueError("current limit exceeds maximum limit")

        monkeypatch.setitem(
            sys.modules, "resource", SimpleNamespace(RLIMIT_AS=9, setrlimit=reject_limit)
        )
    parse_worker.main()
    payload = json.loads(output.getvalue())
    assert [unit["text"] for unit in payload["units"]] == ["name", "value", "Source", "12.50"]
