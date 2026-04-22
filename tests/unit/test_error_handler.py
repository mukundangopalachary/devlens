"""Tests for the centralized CLI error handler."""

from __future__ import annotations

import pytest
import typer

from devlens.cli.error_handler import _emit_error, handle_errors
from devlens.core.errors import (
    ConfigurationError,
    DevLensError,
    InvalidArgumentsError,
    LLMUnavailableError,
    MigrationRequiredError,
    PathSecurityError,
    RetrievalError,
    StaticAnalysisError,
    TaskNotFoundError,
    WatchError,
)


def test_handle_errors_passes_through_on_success() -> None:
    @handle_errors("test")
    def good_command(as_json: bool = False) -> str:
        return "ok"

    assert good_command() == "ok"


def test_handle_errors_catches_devlens_error() -> None:
    @handle_errors("test")
    def bad_command(as_json: bool = False) -> None:
        raise DevLensError("something broke")

    with pytest.raises(typer.Exit):
        bad_command()


def test_handle_errors_catches_subclass_error() -> None:
    @handle_errors("test")
    def bad_command(as_json: bool = False) -> None:
        raise TaskNotFoundError("task #42 not found")

    with pytest.raises(typer.Exit):
        bad_command()


def test_handle_errors_catches_unexpected_exception() -> None:
    @handle_errors("test")
    def bad_command(as_json: bool = False) -> None:
        raise RuntimeError("unexpected")

    with pytest.raises(typer.Exit):
        bad_command()


def test_handle_errors_lets_typer_exit_through() -> None:
    @handle_errors("test")
    def exit_command(as_json: bool = False) -> None:
        raise typer.Exit(code=0)

    with pytest.raises(typer.Exit):
        exit_command()


def test_handle_errors_lets_keyboard_interrupt_through() -> None:
    @handle_errors("test")
    def interrupt_command(as_json: bool = False) -> None:
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        interrupt_command()


def test_error_codes_are_correct() -> None:
    assert DevLensError("x").code == "runtime_error"
    assert InvalidArgumentsError("x").code == "invalid_arguments"
    assert StaticAnalysisError("x").code == "analysis_failed"
    assert TaskNotFoundError("x").code == "task_not_found"
    assert MigrationRequiredError("x").code == "schema_outdated"
    assert LLMUnavailableError("x").code == "llm_unavailable"
    assert WatchError("x").code == "watch_failed"
    assert ConfigurationError("x").code == "config_error"
    assert PathSecurityError("x").code == "invalid_path"
    assert RetrievalError("x").code == "retrieval_failed"


def test_fix_commands_present() -> None:
    assert MigrationRequiredError("x").fix_command == "uv run alembic upgrade head"
    assert LLMUnavailableError("x").fix_command == "ollama serve && ollama pull gemma2:2b"
    assert DevLensError("x").fix_command is None


def test_fix_command_override() -> None:
    err = DevLensError("x", fix_command="do something")
    assert err.fix_command == "do something"


def test_code_override() -> None:
    err = DevLensError("x", code="custom_code")
    assert err.code == "custom_code"


def test_emit_error_json(capsys: pytest.CaptureFixture[str]) -> None:
    _emit_error(
        command_name="test",
        code="test_code",
        message="test message",
        fix_command="run fix",
        as_json=True,
    )
    captured = capsys.readouterr()
    assert '"test_code"' in captured.out
    assert '"test message"' in captured.out
    assert '"run fix"' in captured.out


def test_emit_error_human(capsys: pytest.CaptureFixture[str]) -> None:
    _emit_error(
        command_name="test",
        code="test_code",
        message="test message",
        fix_command="run fix",
        as_json=False,
    )
    captured = capsys.readouterr()
    assert "Error [test_code]: test message" in captured.err
    assert "Fix: run fix" in captured.err
