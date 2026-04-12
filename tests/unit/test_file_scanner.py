from pathlib import Path

from devlens.ingestion.file_scanner import _is_ignored


def test_is_ignored_for_virtualenv_path() -> None:
    assert _is_ignored(Path(".venv/lib/site.py"))


def test_is_not_ignored_for_source_file() -> None:
    assert not _is_ignored(Path("src/devlens/main.py"))
