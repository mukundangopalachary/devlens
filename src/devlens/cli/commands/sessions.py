from __future__ import annotations

import json

import typer
from sqlalchemy.exc import OperationalError

from devlens.cli.json_contract import emit_json_error, success_response
from devlens.storage.db import SessionLocal
from devlens.storage.repositories.chat import list_chat_sessions


def sessions_command(
    limit: int = typer.Option(20, "--limit", min=1, max=100, help="Max sessions to list."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    session = SessionLocal()
    try:
        sessions = list_chat_sessions(session, limit=limit)
    except OperationalError as exc:
        message = _sessions_schema_hint(str(exc))
        if as_json:
            emit_json_error("sessions", "schema_outdated", message)
        typer.echo(message)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        if as_json:
            emit_json_error(
                "sessions", "sessions_failed", "Sessions command failed.", details=str(exc)
            )
        raise
    finally:
        session.close()

    if as_json:
        payload = success_response(
            "sessions",
            {
                "limit": limit,
                "items": [
                    {
                        "id": chat_session.id,
                        "title": chat_session.title,
                        "created_at": chat_session.created_at.isoformat(),
                    }
                    for chat_session in sessions
                ],
            },
        )
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    if not sessions:
        typer.echo("No chat sessions yet.")
        return
    for chat_session in sessions:
        typer.echo(
            f"#{chat_session.id} | {chat_session.created_at.isoformat()} | {chat_session.title}"
        )


def _sessions_schema_hint(error_text: str) -> str:
    lowered = error_text.lower()
    if "no such table: chat_sessions" in lowered:
        return "Chat schema missing. Run: uv run alembic upgrade head"
    return f"Sessions query failed: {error_text}"
