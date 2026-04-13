from pathlib import Path

from devlens.ingestion.file_scanner import (
    _is_extension_allowed,
    _is_ignored,
    _normalize_cli_path,
)


def test_is_ignored_for_virtualenv_path() -> None:
    assert _is_ignored(Path(".venv/lib/site.py"))


def test_is_not_ignored_for_source_file() -> None:
    assert not _is_ignored(Path("src/devlens/main.py"))


def test_normalize_cli_path_strips_at_prefix() -> None:
    assert _normalize_cli_path(Path("@src/devlens/main.py")) == Path("src/devlens/main.py")


def test_normalize_cli_path_keeps_plain_path() -> None:
    assert _normalize_cli_path(Path("src/devlens/main.py")) == Path("src/devlens/main.py")


def test_normalize_cli_path_allows_root_marker() -> None:
    assert _normalize_cli_path(Path("@.")) == Path(".")


def test_is_extension_allowed_respects_allow_all_flag() -> None:
    assert _is_extension_allowed(Path("AGENTS.md"), (".py",), include_all_extensions=True)


def test_is_extension_allowed_uses_configured_extensions() -> None:
    assert not _is_extension_allowed(Path("AGENTS.md"), (".py",), include_all_extensions=False)
