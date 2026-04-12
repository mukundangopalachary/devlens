from typing import Annotated

import typer

from devlens.storage.db import SessionLocal
from devlens.storage.repositories.feedback import list_latest_feedback

LimitOption = Annotated[
    int,
    typer.Option("--limit", min=1, max=50, help="Number of feedback rows."),
]


def feedback_command(
    latest: bool = typer.Option(True, "--latest", help="Show latest feedback."),
    limit: LimitOption = 10,
) -> None:
    if not latest:
        typer.echo("Only latest feedback view exists now. Use `--latest`.")
        return

    session = SessionLocal()
    try:
        feedback_rows = list_latest_feedback(session, limit=limit)
    finally:
        session.close()

    if not feedback_rows:
        typer.echo("No feedback recorded yet. Run `devlens analyze <path>` first.")
        return

    for feedback, _, submission in feedback_rows:
        typer.echo(f"- [{feedback.kind}] {submission.file_path}: {feedback.content}")
