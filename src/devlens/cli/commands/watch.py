from __future__ import annotations

import json
from pathlib import Path
from threading import Event
from typing import Annotated

import typer

from devlens.cli.json_contract import emit_json_error, success_response
from devlens.storage.db import SessionLocal
from devlens.watch.service import run_watch_loop

PathArgument = Annotated[Path, typer.Argument(resolve_path=True)]


def watch_command(
    path: PathArgument = Path("."),
    mode: str = typer.Option("git", "--mode", help="Watch mode: git or save."),
    interval: float = typer.Option(1.0, "--interval", min=0.2, help="Polling interval seconds."),
    loops: int = typer.Option(0, "--loops", min=0, help="Max loops (0 means infinite)."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    if mode not in {"git", "save"}:
        if as_json:
            emit_json_error("watch", "invalid_arguments", "--mode must be git or save.")
        raise typer.BadParameter("--mode must be git or save")

    if not path.exists():
        if as_json:
            emit_json_error("watch", "invalid_path", f"Path not found: {path}")
        raise typer.BadParameter(f"Path not found: {path}")

    session = SessionLocal()
    stop_event = Event()
    if loops > 0:
        # bounded loop support for testing/automation users
        _start_bounded_stop_thread(stop_event, interval=interval, loops=loops)

    try:
        stats = run_watch_loop(
            session,
            path,
            mode=mode,
            interval_seconds=interval,
            stop_event=stop_event,
        )
    except KeyboardInterrupt:
        stop_event.set()
        stats = {
            "loops": 0,
            "queued": 0,
            "analyzed": 0,
            "errors": 0,
            "skipped": 0,
        }
    except Exception as exc:
        session.rollback()
        if as_json:
            emit_json_error("watch", "watch_failed", "Watch command failed.", details=str(exc))
        raise
    finally:
        session.close()

    if as_json:
        payload = success_response(
            "watch",
            {
                "path": str(path),
                "mode": mode,
                "interval": interval,
                "loops_limit": loops,
                "stats": stats,
            },
        )
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    typer.echo(
        "watch complete | "
        f"loops={stats['loops']} queued={stats['queued']} analyzed={stats['analyzed']} "
        f"errors={stats['errors']} skipped={stats['skipped']}"
    )


def _start_bounded_stop_thread(stop_event: Event, *, interval: float, loops: int) -> None:
    from threading import Thread
    from time import sleep

    def stopper() -> None:
        sleep(max(interval * loops, 0.2))
        stop_event.set()

    Thread(target=stopper, daemon=True).start()
