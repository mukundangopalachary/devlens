from typing import Annotated

import typer

from devlens.storage.db import SessionLocal
from devlens.storage.repositories.skills import get_skill_history

LimitOption = Annotated[int, typer.Option("--limit", min=1, max=50, help="Number of history rows.")]


def history_command(limit: LimitOption = 10) -> None:
    session = SessionLocal()
    try:
        history_rows = get_skill_history(session, limit=limit)
    finally:
        session.close()

    if not history_rows:
        typer.echo("No skill history recorded yet. Run `devlens analyze <path>` first.")
        return

    for history, skill in history_rows:
        typer.echo(
            f"- {history.recorded_at.isoformat()} | {skill.name}: "
            f"{history.previous_score:.2f} -> {history.new_score:.2f} "
            f"(delta {history.delta:.2f})"
        )
