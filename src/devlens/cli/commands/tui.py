from __future__ import annotations

from pathlib import Path

import typer


def tui_command() -> None:
    tui_dir = Path(__file__).resolve().parents[4] / "tui"
    if not tui_dir.exists():
        raise typer.BadParameter(f"TUI directory not found: {tui_dir}")

    import subprocess

    result = subprocess.run(["go", "run", "."], cwd=tui_dir, check=False)
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)
