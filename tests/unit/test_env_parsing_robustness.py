from __future__ import annotations

from devlens.config import get_settings


def test_quoted_values_with_spaces(monkeypatch: object) -> None:
    monkeypatch.setenv("DEVLENS_LOG_LEVEL", ' "DEBUG" ')
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.log_level == "DEBUG"


def test_nested_quotes(monkeypatch: object) -> None:
    monkeypatch.setenv("DEVLENS_LOG_LEVEL", '"\'DEBUG\'"')
    get_settings.cache_clear()
    settings = get_settings()
    # '"\'DEBUG\'"' -> [1:-1] -> "'DEBUG'"
    assert settings.log_level == "'DEBUG'"


def test_empty_string_fallback(monkeypatch: object) -> None:
    monkeypatch.setenv("DEVLENS_LOG_LEVEL", "")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.log_level == "INFO"


def test_whitespace_string_fallback(monkeypatch: object) -> None:
    monkeypatch.setenv("DEVLENS_LOG_LEVEL", "   ")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.log_level == "INFO"


def test_non_placeholder_with_brackets(monkeypatch: object) -> None:
    monkeypatch.setenv("DEVLENS_LOG_LEVEL", "<NOT_A_REAL_PLACEHOLDER>")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.log_level == "INFO"


def test_project_root_behavior(monkeypatch: object) -> None:
    monkeypatch.setenv("DEVLENS_PROJECT_ROOT", "<DEFAULT>")
    get_settings.cache_clear()
    settings = get_settings()
    assert "<DEFAULT>" not in str(settings.resolved_project_root)
