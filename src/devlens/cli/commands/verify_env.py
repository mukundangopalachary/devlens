from __future__ import annotations

import json
import shutil
import sys
from typing import Any

import typer

from devlens.cli.error_handler import handle_errors
from devlens.cli.json_contract import error_response, success_response
from devlens.config import get_settings
from devlens.health import collect_health_snapshot


@handle_errors("verify-env")
def verify_env_command(
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    checks = collect_env_checks()
    all_ok = _all_required_checks_ok(checks)
    payload = {"all_ok": all_ok, "checks": checks}

    if as_json:
        if all_ok:
            typer.echo(
                json.dumps(success_response("verify-env", payload), sort_keys=True, indent=2)
            )
            return
        typer.echo(
            json.dumps(
                error_response(
                    "verify-env",
                    "verification_failed",
                    "Environment verification failed.",
                    details=payload,
                ),
                sort_keys=True,
                indent=2,
            )
        )
        raise typer.Exit(code=1)

    for name, details in checks.items():
        status = "ok" if bool(details["ok"]) else "fail"
        required = "required" if bool(details["required"]) else "optional"
        typer.echo(f"{name}: {status} ({required})")
        typer.echo(f"  details: {details['details']}")
        if not bool(details["ok"]) and details["fix"] is not None:
            typer.echo(f"  fix: {details['fix']}")

    if not all_ok:
        raise typer.Exit(code=1)


def collect_env_checks() -> dict[str, dict[str, object]]:
    settings = get_settings()
    project_root = settings.resolved_project_root
    snapshot = collect_health_snapshot()
    db_check = _read_health_check(snapshot, "database")
    ollama_check = _read_health_check(snapshot, "ollama")

    python_ok = _python_supported()
    return {
        "python": {
            "ok": python_ok,
            "required": True,
            "details": f"running {sys.version.split()[0]}",
            "fix": "install Python 3.12+" if not python_ok else None,
        },
        "uv": {
            "ok": shutil.which("uv") is not None,
            "required": True,
            "details": "uv command available" if shutil.which("uv") else "uv command missing",
            "fix": "install uv: https://docs.astral.sh/uv/",
        },
        "git": {
            "ok": shutil.which("git") is not None,
            "required": True,
            "details": "git command available" if shutil.which("git") else "git command missing",
            "fix": "install git",
        },
        "go": {
            "ok": shutil.which("go") is not None,
            "required": False,
            "details": "go command available" if shutil.which("go") else "go command missing",
            "fix": "install go for TUI support",
        },
        "venv": {
            "ok": (project_root / ".venv").exists(),
            "required": True,
            "details": str(project_root / ".venv"),
            "fix": "bash scripts/bootstrap.sh",
        },
        "env_file": {
            "ok": (project_root / ".env").exists(),
            "required": True,
            "details": str(project_root / ".env"),
            "fix": "cp .env.example .env",
        },
        "database": {
            "ok": db_check.get("status") == "ok",
            "required": True,
            "details": db_check.get("summary", "database check unavailable"),
            "fix": "uv run alembic upgrade head",
        },
        "ollama": {
            "ok": ollama_check.get("status") == "ok",
            "required": False,
            "details": ollama_check.get("summary", "ollama check unavailable"),
            "fix": "ollama serve && ollama pull gemma2:2b && ollama pull nomic-embed-text",
        },
    }


def _python_supported() -> bool:
    return sys.version_info.major == 3 and sys.version_info.minor >= 12


def _read_health_check(snapshot: dict[str, object], key: str) -> dict[str, Any]:
    checks = snapshot.get("checks", {})
    if not isinstance(checks, dict):
        return {}
    value = checks.get(key, {})
    if not isinstance(value, dict):
        return {}
    return value


def _all_required_checks_ok(checks: dict[str, dict[str, object]]) -> bool:
    return all(bool(item["ok"]) for item in checks.values() if bool(item["required"]))
