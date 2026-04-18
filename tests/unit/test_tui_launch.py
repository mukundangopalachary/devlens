from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from devlens.cli.commands.start import start_command
from devlens.cli.commands.tui import tui_command


def test_tui_command_no_go(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda x: None if x == "go" else "/usr/bin/which")

    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "__truediv__", return_value=MagicMock(exists=lambda: True)):
            with pytest.raises(typer.Exit) as exc:
                tui_command()
            assert exc.value.exit_code == 1


def test_tui_command_missing_dir() -> None:
    with patch.object(Path, "exists", return_value=False):
        with pytest.raises(typer.Exit) as exc:
            tui_command()
        assert exc.value.exit_code == 1


def test_start_command_invalid_mode() -> None:
    with pytest.raises(typer.Exit) as exc:
        start_command(mode="invalid")
    assert exc.value.exit_code == 1


@patch("subprocess.run")
@patch("devlens.cli.commands.start.doctor_command")
def test_start_command_migration_failure(mock_doctor: MagicMock, mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(returncode=1)

    with pytest.raises(typer.Exit) as exc:
        start_command(mode="chat", skip_doctor=True)
    assert exc.value.exit_code == 1
    assert mock_run.call_count == 1
    assert "alembic" in mock_run.call_args[0][0]
