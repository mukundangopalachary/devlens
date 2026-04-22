from __future__ import annotations

import json
from typing import cast

import typer

from devlens.cli.json_contract import emit_json_error, success_response
from devlens.storage.db import SessionLocal
from devlens.storage.repositories.reporting import build_report_snapshot


def report_command(
    days: int = typer.Option(14, "--days", min=1, max=365, help="Report window in days."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Top theme/file item count."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    session = SessionLocal()
    try:
        snapshot = build_report_snapshot(session, days=days, limit=limit)
    except Exception as exc:
        if as_json:
            emit_json_error(
                "report",
                "report_failed",
                "Report command failed.",
                details=str(exc),
            )
        raise
    finally:
        session.close()

    if as_json:
        payload = success_response("report", snapshot)
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    analyses_by_day = cast(list[dict[str, object]], snapshot["analyses_by_day"])
    recurring_issue_themes = cast(list[dict[str, object]], snapshot["recurring_issue_themes"])
    recurring_task_themes = cast(list[dict[str, object]], snapshot["recurring_task_themes"])
    task_summary = cast(dict[str, object], snapshot["task_summary"])
    top_touched_files = cast(list[dict[str, object]], snapshot["top_touched_files"])

    typer.echo(f"report_window_days: {snapshot['window_days']}")
    typer.echo(f"range: {snapshot['from']} -> {snapshot['to']}")
    typer.echo(f"analyses_total: {snapshot['analyses_total']}")

    typer.echo("\nanalyses_by_day:")
    for row in analyses_by_day:
        typer.echo(f"- {row['date']}: {row['count']}")

    typer.echo("\nrecurring_issue_themes:")
    for row in recurring_issue_themes:
        typer.echo(f"- {row['theme']}: {row['count']}")

    typer.echo("\nrecurring_task_themes:")
    for row in recurring_task_themes:
        typer.echo(f"- {row['theme']}: {row['count']}")

    typer.echo("\ntask_summary:")
    typer.echo(
        f"- total={task_summary['total']} done={task_summary['done']} "
        f"pending={task_summary['pending']} completion_rate={task_summary['completion_rate']}"
    )

    typer.echo("\ntop_touched_files:")
    for row in top_touched_files:
        typer.echo(f"- {row['file_path']}: {row['analysis_count']}")
