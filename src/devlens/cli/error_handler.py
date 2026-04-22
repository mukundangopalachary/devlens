"""Centralized CLI error handler.

Wraps CLI commands to catch DevLensError subtypes and emit
consistent JSON or human-readable error output with actionable
fix commands.
"""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

import typer

from devlens.cli.json_contract import error_response
from devlens.core.errors import DevLensError

P = ParamSpec("P")
T = TypeVar("T")


def handle_errors(command_name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that catches DevLensError and emits standardised output.

    Usage::

        @handle_errors("analyze")
        def analyze_command(..., as_json: bool = ...) -> None:
            ...

    The wrapped function MUST accept ``as_json`` as a keyword argument
    (or positional — we inspect kwargs first, then scan args by type).
    """

    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return fn(*args, **kwargs)
            except typer.Exit:
                raise
            except SystemExit:
                raise
            except KeyboardInterrupt:
                raise
            except DevLensError as exc:
                _emit_error(
                    command_name=command_name,
                    code=exc.code,
                    message=str(exc),
                    fix_command=exc.fix_command,
                    as_json=_extract_as_json(kwargs),
                )
                raise typer.Exit(code=1) from exc
            except Exception as exc:
                _emit_error(
                    command_name=command_name,
                    code="runtime_error",
                    message=str(exc),
                    fix_command=None,
                    as_json=_extract_as_json(kwargs),
                )
                raise typer.Exit(code=1) from exc

        return wrapper

    return decorator


def _extract_as_json(kwargs: dict[str, Any]) -> bool:
    """Pull as_json from kwargs. Defaults to False."""
    return bool(kwargs.get("as_json", False))


def _emit_error(
    *,
    command_name: str,
    code: str,
    message: str,
    fix_command: str | None,
    as_json: bool,
) -> None:
    """Emit error in JSON or human-readable format."""
    if as_json:
        payload = error_response(command_name, code, message)
        if fix_command:
            payload["errors"][0]["fix"] = fix_command
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    typer.echo(f"Error [{code}]: {message}", err=True)
    if fix_command:
        typer.echo(f"  Fix: {fix_command}", err=True)
