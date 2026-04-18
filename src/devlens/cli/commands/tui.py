from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer


def tui_command() -> None:
    repo_root = _detect_repo_root()
    tui_dir = repo_root / "tui"
    if not tui_dir.exists():
        typer.echo(f"Error: TUI directory not found: {tui_dir}", err=True)
        raise typer.Exit(code=1)

    if not (tui_dir / "main.go").exists():
        typer.echo(f"Error: TUI source file 'main.go' not found in {tui_dir}", err=True)
        raise typer.Exit(code=1)

    if not shutil.which("go"):
        typer.echo("Error: 'go' executable not found in PATH.", err=True)
        typer.echo("Fix: Install Go (https://go.dev/doc/install) to run the TUI.", err=True)
        raise typer.Exit(code=1)

    typer.echo("Starting DevLens TUI...")
    result = subprocess.run(["go", "run", "."], cwd=tui_dir, check=False)
    if result.returncode != 0:
        typer.echo(f"TUI exited with non-zero code: {result.returncode}", err=True)
        raise typer.Exit(code=result.returncode)


def _detect_repo_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path(__file__).resolve().parents[4]
