from __future__ import annotations

from pathlib import Path

from devlens.chat.service import _normalize_file_scope


def test_normalize_file_scope_returns_relative_path() -> None:
    root = Path(".").resolve()
    scoped = _normalize_file_scope("src/devlens/logging.py", root)
    assert scoped == "src/devlens/logging.py"


def test_normalize_file_scope_strips_at_prefix() -> None:
    root = Path(".").resolve()
    scoped = _normalize_file_scope("@src/devlens/logging.py", root)
    assert scoped == "src/devlens/logging.py"
