from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

import typer

from devlens.cli.json_contract import error_response, success_response


@dataclass(frozen=True)
class Probe:
    name: str
    args: list[str]
    required: bool
    description: str


def smoke_test_command(
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Include chat probe that needs model runtime.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    probes = _default_probes(strict=strict)
    results = [_run_probe(probe) for probe in probes]

    required_failed = [item for item in results if item["required"] and not item["ok"]]
    payload = {
        "strict": strict,
        "all_required_ok": len(required_failed) == 0,
        "results": results,
    }

    if as_json:
        if len(required_failed) == 0:
            typer.echo(
                json.dumps(success_response("smoke-test", payload), sort_keys=True, indent=2)
            )
            return
        typer.echo(
            json.dumps(
                error_response(
                    "smoke-test",
                    "smoke_failed",
                    "One or more required probes failed.",
                    details=payload,
                ),
                sort_keys=True,
                indent=2,
            )
        )
        raise typer.Exit(code=1)

    for item in results:
        status = "ok" if item["ok"] else "fail"
        required = "required" if item["required"] else "optional"
        typer.echo(f"{item['name']}: {status} ({required})")
        typer.echo(f"  command: {item['command']}")
        if not item["ok"]:
            typer.echo(f"  details: {item['details']}")

    if required_failed:
        raise typer.Exit(code=1)


def _default_probes(strict: bool) -> list[Probe]:
    probes = [
        Probe(
            name="verify-env",
            args=["verify-env", "--json"],
            required=True,
            description="environment integrity",
        ),
        Probe(
            name="doctor",
            args=["doctor", "--json"],
            required=True,
            description="health snapshot",
        ),
        Probe(
            name="tasks",
            args=["tasks", "--limit", "1", "--json"],
            required=True,
            description="task command wiring",
        ),
        Probe(
            name="sessions",
            args=["sessions", "--limit", "1", "--json"],
            required=True,
            description="session list command",
        ),
    ]
    if strict:
        probes.append(
            Probe(
                name="ask",
                args=["ask", "health check question", "--json"],
                required=False,
                description="chat llm path",
            )
        )
    return probes


def _run_probe(probe: Probe) -> dict[str, object]:
    command = ["uv", "run", "devlens", *probe.args]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output = (completed.stdout or "") + (completed.stderr or "")
    ok = completed.returncode == 0
    return {
        "name": probe.name,
        "description": probe.description,
        "required": probe.required,
        "ok": ok,
        "command": " ".join(command),
        "details": output.strip()[:1000],
    }
