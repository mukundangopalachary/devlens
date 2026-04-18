from __future__ import annotations

import subprocess
from pathlib import Path

import typer

from devlens.cli.commands.doctor import doctor_command


def start_command(
    mode: str = typer.Option("tui", "--mode", help="Start mode: tui or chat."),
    skip_doctor: bool = typer.Option(False, "--skip-doctor", help="Skip health checks."),
) -> None:
    if mode not in {"tui", "chat"}:
        typer.echo(f"Error: Invalid mode '{mode}'. Use 'tui' or 'chat'.", err=True)
        raise typer.Exit(code=1)

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
        typer.echo("Error: Database migration failed.", err=True)
        typer.echo("Fix: Run 'uv run alembic upgrade head' manually.", err=True)
        raise typer.Exit(code=migrate.returncode)

    typer.echo(f"Launching {mode}...")
    if mode == "tui":
        launch = subprocess.run(["uv", "run", "devlens", "tui"], cwd=repo_root, check=False)
    else:
        launch = subprocess.run(["uv", "run", "devlens", "chat"], cwd=repo_root, check=False)

    if launch.returncode != 0:
        typer.echo(f"Error: {mode} failed to launch or exited with error.", err=True)
        raise typer.Exit(code=launch.returncode)


def _detect_repo_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return current
