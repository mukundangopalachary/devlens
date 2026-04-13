from __future__ import annotations

import json

import typer

from devlens.cli.json_contract import emit_json_error, success_response
from devlens.health import collect_health_report, collect_health_snapshot


def doctor_command(
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    try:
        snapshot = collect_health_snapshot()
    except Exception as exc:
        if as_json:
            emit_json_error(
                "doctor",
                "doctor_failed",
                "Doctor command failed.",
                details=str(exc),
            )
        raise

    if as_json:
        payload = success_response("doctor", snapshot)
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    report = collect_health_report(snapshot=snapshot)
    for line in report:
        typer.echo(line)
