import json
from pathlib import Path
from typing import Annotated

import typer

from devlens.analysis.pipeline import run_static_analysis, run_static_analysis_for_changed_files
from devlens.cli.json_contract import emit_json_error, success_response
from devlens.storage.db import SessionLocal

PathArgument = Annotated[Path, typer.Argument(resolve_path=True)]


def analyze_command(
    path: PathArgument = Path("."),
    changed: bool = typer.Option(False, "--changed", help="Analyze only changed files."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    if not path.exists():
        if as_json:
            emit_json_error("analyze", "invalid_path", f"Path not found: {path}")
        raise typer.BadParameter(f"Path not found: {path}")

    session = SessionLocal()
    try:
        if changed:
            summary, analyses = run_static_analysis_for_changed_files(path, session)
        else:
            summary, analyses = run_static_analysis(path, session)
    except Exception as exc:
        if as_json:
            emit_json_error(
                "analyze",
                "analyze_failed",
                "Analyze command failed.",
                details=str(exc),
            )
        raise
    finally:
        session.close()

    if as_json:
        payload = success_response(
            "analyze",
            {
                "path": str(path),
                "changed": changed,
                "summary": summary.model_dump(mode="json"),
                "analyses": [
                    {
                        "relative_path": str(result.relative_path),
                        "metrics": result.metrics.model_dump(mode="json"),
                        "critique": result.feedback.critique
                        if result.feedback is not None
                        else None,
                    }
                    for result in analyses
                ],
            },
        )
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    typer.echo(
        "\n".join(
            [
                f"Analyzed {summary.files_analyzed} file(s) from {path}.",
                "Saved "
                f"{summary.submissions_saved} submission(s) and "
                f"{summary.analyses_saved} analysis result(s).",
                f"Deduplicated files: {summary.deduplicated_files}",
                f"Total complexity: {summary.total_complexity:.1f}",
                f"Max nesting depth: {summary.max_nesting_depth}",
                f"Files with recursion: {summary.recursion_file_count}",
            ]
        )
    )
    for result in analyses[:10]:
        typer.echo(
            f"- {result.relative_path}: complexity={result.metrics.cyclomatic_complexity:.1f}, "
            f"loops={result.metrics.loop_count}, "
            f"functions={result.metrics.function_count}, "
            f"nesting={result.metrics.max_nesting_depth}"
        )
        if result.feedback is not None:
            typer.echo(f"  critique: {result.feedback.critique}")
