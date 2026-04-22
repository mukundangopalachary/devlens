from __future__ import annotations

import json

import typer

from devlens.cli.error_handler import handle_errors
from devlens.cli.json_contract import success_response
from devlens.health import collect_health_report, collect_health_snapshot


@handle_errors("doctor")
def doctor_command(
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
    setup: bool = typer.Option(False, "--setup", help="Print setup fix commands."),
) -> None:
    snapshot = collect_health_snapshot()

    if as_json:
        payload = success_response("doctor", snapshot)
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    report = collect_health_report(snapshot=snapshot)
    for line in report:
        typer.echo(line)

    if setup:
        typer.echo("\nsetup_fixes:")
        checks = snapshot.get("checks", {})
        if isinstance(checks, dict):
            ollama_check = checks.get("ollama", {})
            qdrant_check = checks.get("qdrant", {})
            database_check = checks.get("database", {})

            if isinstance(database_check, dict) and database_check.get("status") != "ok":
                typer.echo("- uv run alembic upgrade head")
            if isinstance(ollama_check, dict) and ollama_check.get("status") != "ok":
                typer.echo("- ollama serve")
                typer.echo("- ollama pull gemma2:2b")
                typer.echo("- ollama pull nomic-embed-text")
            if isinstance(qdrant_check, dict) and qdrant_check.get("status") != "ok":
                typer.echo("- uv run devlens reindex")
