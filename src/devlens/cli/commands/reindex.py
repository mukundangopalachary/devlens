from __future__ import annotations

import json

import typer

from devlens.cli.json_contract import emit_json_error, success_response
from devlens.config import get_settings
from devlens.retrieval.qdrant_store import qdrant_available
from devlens.storage.db import SessionLocal
from devlens.storage.repositories.knowledge import reindex_qdrant


def reindex_command(
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    settings = get_settings()
    if settings.vector_backend != "qdrant":
        message = (
            f"Reindex supports only qdrant backend. Current backend: {settings.vector_backend}."
        )
        if as_json:
            emit_json_error("reindex", "unsupported_backend", message)
        typer.echo(message)
        raise typer.Exit(code=1)

    if not qdrant_available():
        message = "Qdrant client unavailable. Install/enable qdrant-client first."
        if as_json:
            emit_json_error("reindex", "qdrant_unavailable", message)
        typer.echo(message)
        raise typer.Exit(code=1)

    session = SessionLocal()
    try:
        stats = reindex_qdrant(session)
        session.commit()
    except Exception as exc:
        session.rollback()
        if as_json:
            emit_json_error(
                "reindex",
                "reindex_failed",
                "Reindex command failed.",
                details=str(exc),
            )
        raise
    finally:
        session.close()

    if as_json:
        payload = success_response(
            "reindex",
            {
                "vector_backend": settings.vector_backend,
                "qdrant_collection": settings.qdrant_collection,
                "stats": stats,
            },
        )
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    typer.echo("Qdrant reindex complete.")
    typer.echo(
        " | ".join(
            [
                f"documents={stats['documents_total']}",
                f"chunks={stats['chunks_total']}",
                f"embedded={stats['embedded_chunks']}",
                f"indexed={stats['indexed_chunks']}",
                f"skipped={stats['skipped_chunks']}",
                f"deduped={stats['deduplicated_chunks']}",
            ]
        )
    )
