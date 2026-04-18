from __future__ import annotations

from pathlib import Path

from devlens.cli.commands.start import _detect_repo_root as detect_start_root
from devlens.cli.commands.tui import _detect_repo_root as detect_tui_root


def test_detect_repo_root_for_start_has_pyproject() -> None:
    root = detect_start_root()
    assert (root / "pyproject.toml").exists()


def test_detect_repo_root_for_tui_has_pyproject() -> None:
    root = detect_tui_root()
    assert (root / "pyproject.toml").exists()


def test_detected_roots_are_absolute() -> None:
    assert detect_start_root().is_absolute()
    assert detect_tui_root().is_absolute()
    assert isinstance(detect_start_root(), Path)
