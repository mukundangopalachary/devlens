from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from devlens.chat.service import ingest_files_into_knowledge_base
from devlens.cli.json_contract import emit_json_error, success_response
from devlens.storage.db import SessionLocal

FileArgument = Annotated[list[Path], typer.Argument(resolve_path=True)]


def ingest_command(
    files: FileArgument,
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    session = SessionLocal()
    try:
        active_session_id = None
        stored_files = ingest_files_into_knowledge_base(
            session,
            files,
            session_id=active_session_id,
        )
    except Exception as exc:
        if as_json:
            emit_json_error(
                "ingest",
                "ingest_failed",
                "Ingest command failed.",
                details=str(exc),
            )
        raise
    finally:
        session.close()

    if as_json:
        payload = success_response(
            "ingest",
            {
                "requested": [str(item) for item in files],
                "loaded_count": len(stored_files),
                "loaded_files": stored_files,
            },
        )
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    typer.echo(f"[knowledge] loaded {len(stored_files)} file(s)")
    if stored_files:
        for file_path in stored_files:
            typer.echo(f"- {file_path}")
