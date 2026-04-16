from __future__ import annotations

import subprocess

import typer

from devlens.cli.commands.doctor import doctor_command


def start_command(
    mode: str = typer.Option("tui", "--mode", help="Start mode: tui or chat."),
) -> None:
    if mode not in {"tui", "chat"}:
        raise typer.BadParameter("--mode must be tui or chat")

    doctor_command(as_json=False)

    migrate = subprocess.run(["uv", "run", "alembic", "upgrade", "head"], check=False)
    if migrate.returncode != 0:
        typer.echo("Migration failed. Run: uv run alembic upgrade head")
        raise typer.Exit(code=migrate.returncode)

    if mode == "tui":
        launch = subprocess.run(["uv", "run", "devlens", "tui"], check=False)
    else:
        launch = subprocess.run(["uv", "run", "devlens", "chat"], check=False)

    if launch.returncode != 0:
        raise typer.Exit(code=launch.returncode)
