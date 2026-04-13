import json
from typing import Annotated

import typer

from devlens.cli.json_contract import emit_json_error, success_response
from devlens.storage.db import SessionLocal
from devlens.storage.repositories.skills import get_skill_history

LimitOption = Annotated[int, typer.Option("--limit", min=1, max=50, help="Number of history rows.")]


def history_command(
    limit: LimitOption = 10,
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    session = SessionLocal()
    try:
        history_rows = get_skill_history(session, limit=limit)
    except Exception as exc:
        if as_json:
            emit_json_error(
                "history",
                "history_failed",
                "History command failed.",
                details=str(exc),
            )
        raise
    finally:
        session.close()

    if as_json:
        payload = success_response(
            "history",
            {
                "limit": limit,
                "items": [
                    {
                        "recorded_at": history.recorded_at.isoformat(),
                        "skill": skill.name,
                        "previous_score": history.previous_score,
                        "new_score": history.new_score,
                        "delta": history.delta,
                    }
                    for history, skill in history_rows
                ],
            },
        )
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    if not history_rows:
        typer.echo("No skill history recorded yet. Run `devlens analyze <path>` first.")
        return

    for history, skill in history_rows:
        typer.echo(
            f"- {history.recorded_at.isoformat()} | {skill.name}: "
            f"{history.previous_score:.2f} -> {history.new_score:.2f} "
            f"(delta {history.delta:.2f})"
        )
