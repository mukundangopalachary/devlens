from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import typer

CONTRACT_VERSION = "v1"


def success_response(command: str, data: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "version": CONTRACT_VERSION,
        "timestamp": _timestamp_utc(),
        "data": data,
        "errors": [],
    }


def error_response(
    command: str,
    code: str,
    message: str,
    *,
    details: Any | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "command": command,
        "version": CONTRACT_VERSION,
        "timestamp": _timestamp_utc(),
        "data": {},
        "errors": [
            {
                "code": code,
                "message": message,
            }
        ],
    }
    if details is not None:
        payload["errors"][0]["details"] = details
    return payload


def _timestamp_utc() -> str:
    return datetime.now(UTC).isoformat()


def emit_json_error(
    command: str,
    code: str,
    message: str,
    *,
    details: Any | None = None,
    exit_code: int = 1,
) -> None:
    typer.echo(
        json.dumps(
            error_response(command, code, message, details=details),
            sort_keys=True,
            indent=2,
        )
    )
    raise typer.Exit(code=exit_code)
