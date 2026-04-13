import json
from typing import Annotated

import typer

from devlens.cli.json_contract import emit_json_error, success_response
from devlens.storage.db import SessionLocal
from devlens.storage.repositories.feedback import list_latest_feedback

LimitOption = Annotated[
    int,
    typer.Option("--limit", min=1, max=50, help="Number of feedback rows."),
]


def feedback_command(
    latest: bool = typer.Option(True, "--latest", help="Show latest feedback."),
    limit: LimitOption = 10,
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    if not latest:
        if as_json:
            emit_json_error(
                "feedback",
                "invalid_arguments",
                "Only latest feedback view exists now. Use --latest.",
            )
        typer.echo("Only latest feedback view exists now. Use `--latest`.")
        raise typer.Exit(code=1)

    session = SessionLocal()
    try:
        feedback_rows = list_latest_feedback(session, limit=limit)
    except Exception as exc:
        if as_json:
            emit_json_error(
                "feedback",
                "feedback_failed",
                "Feedback command failed.",
                details=str(exc),
            )
        raise
    finally:
        session.close()

    if as_json:
        payload = success_response(
            "feedback",
            {
                "latest": latest,
                "limit": limit,
                "items": [
                    {
                        "kind": feedback.kind,
                        "file_path": submission.file_path,
                        "content": feedback.content,
                    }
                    for feedback, _, submission in feedback_rows
                ],
            },
        )
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    if not feedback_rows:
        typer.echo("No feedback recorded yet. Run `devlens analyze <path>` first.")
        return

    for feedback, _, submission in feedback_rows:
        typer.echo(f"- [{feedback.kind}] {submission.file_path}: {feedback.content}")
