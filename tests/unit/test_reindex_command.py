import json
from types import SimpleNamespace

import pytest
import typer

import devlens.cli.commands.reindex as reindex_module


def test_reindex_json_unsupported_backend_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        reindex_module,
        "get_settings",
        lambda: SimpleNamespace(vector_backend="sqlite", qdrant_collection="devlens_knowledge"),
    )

    with pytest.raises(typer.Exit) as exc_info:
        reindex_module.reindex_command(as_json=True)

    assert exc_info.value.exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["command"] == "reindex"
    assert payload["errors"][0]["code"] == "unsupported_backend"
