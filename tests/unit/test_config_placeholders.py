from __future__ import annotations

from devlens.config import get_settings


def test_placeholder_values_fallback_to_defaults(monkeypatch: object) -> None:
    monkeypatch.setenv("DEVLENS_MAX_FILE_SIZE_KB", "<512>")
    monkeypatch.setenv("DEVLENS_OLLAMA_NUM_CTX", "<2048>")
    monkeypatch.setenv("DEVLENS_CACHE_ENABLED", "<true>")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.max_file_size_kb == 512
    assert settings.ollama_num_ctx == 2048
    assert settings.cache_enabled is True


def test_explicit_invalid_int_raises_runtime_error(monkeypatch: object) -> None:
    monkeypatch.setenv("DEVLENS_MAX_FILE_SIZE_KB", "not-an-int")
    get_settings.cache_clear()

    try:
        get_settings()
        raise AssertionError("expected RuntimeError for invalid integer env")
    except RuntimeError as exc:
        assert "DEVLENS_MAX_FILE_SIZE_KB" in str(exc)
    finally:
        monkeypatch.delenv("DEVLENS_MAX_FILE_SIZE_KB", raising=False)
        get_settings.cache_clear()


def test_explicit_invalid_bool_raises_runtime_error(monkeypatch: object) -> None:
    monkeypatch.setenv("DEVLENS_CACHE_ENABLED", "maybe")
    get_settings.cache_clear()

    try:
        get_settings()
        raise AssertionError("expected RuntimeError for invalid boolean env")
    except RuntimeError as exc:
        assert "DEVLENS_CACHE_ENABLED" in str(exc)
    finally:
        monkeypatch.delenv("DEVLENS_CACHE_ENABLED", raising=False)
        get_settings.cache_clear()
