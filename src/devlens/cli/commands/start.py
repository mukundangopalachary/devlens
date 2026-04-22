from __future__ import annotations

import subprocess
from pathlib import Path

import typer

from devlens.cli.commands.doctor import doctor_command
from devlens.cli.error_handler import handle_errors
from devlens.core.errors import DevLensError, MigrationRequiredError


@handle_errors("start")
def start_command(
    mode: str = typer.Option("tui", "--mode", help="Start mode: tui or chat."),
    skip_doctor: bool = typer.Option(False, "--skip-doctor", help="Skip health checks."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    if mode not in {"tui", "chat"}:
        raise DevLensError(f"Invalid mode '{mode}'. Use 'tui' or 'chat'.")

    if not skip_doctor:
        typer.echo("Checking environment...")
        doctor_command(as_json=False)

    repo_root = _detect_repo_root()
    typer.echo("Ensuring database is up to date...")
    migrate = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=repo_root,
        check=False,
    )
    if migrate.returncode != 0:
        raise MigrationRequiredError("Database migration failed.")

    typer.echo(f"Launching {mode}...")
    if mode == "tui":
        launch = subprocess.run(["uv", "run", "devlens", "tui"], cwd=repo_root, check=False)
    else:
        launch = subprocess.run(["uv", "run", "devlens", "chat"], cwd=repo_root, check=False)

    if launch.returncode != 0:
        raise DevLensError(f"{mode} failed to launch or exited with error.")


def _detect_repo_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return current
