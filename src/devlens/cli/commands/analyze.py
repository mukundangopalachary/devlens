from pathlib import Path

import typer


def analyze_command(
    path: Path = typer.Argument(Path("."), exists=True, resolve_path=True),
    changed: bool = typer.Option(False, "--changed", help="Analyze only changed files."),
) -> None:
    mode = "changed files" if changed else "target path"
    typer.echo(f"Analyze stub. Mode: {mode}. Path: {path}")

