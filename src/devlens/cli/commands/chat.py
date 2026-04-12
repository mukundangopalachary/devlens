from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from devlens.chat.service import (
    answer_question,
    complete_task,
    delete_task,
    get_chat_status_line,
    get_task_lines,
    ingest_files_into_knowledge_base,
    start_chat_session,
)
from devlens.storage.db import SessionLocal

FileArgument = Annotated[list[Path], typer.Argument(resolve_path=True)]


def chat_command(files: FileArgument | None = None) -> None:
    session = SessionLocal()
    try:
        session_id = start_chat_session(session)
        initial_files = [] if files is None else files
        if initial_files:
            stored_files = ingest_files_into_knowledge_base(session, initial_files)
            typer.echo(f"[knowledge] loaded {len(stored_files)} file(s)")

        typer.echo("DevLens Chat")
        typer.echo("commands: :add <path>  :tasks  :done <id>  :rm <id>  :help  :exit")
        typer.echo(get_chat_status_line())
        while True:
            user_input = typer.prompt("you>").strip()
            if not user_input:
                continue
            if user_input == ":exit":
                typer.echo("bye")
                break
            if user_input == ":help":
                typer.echo(
                    "Ask normal coding questions or file-specific doubts.\n"
                    ":add <path> ingest file into knowledge base\n"
                    ":tasks show tasks\n"
                    ":done <id> mark task done\n"
                    ":rm <id> remove task\n"
                    ":exit quit chat"
                )
                continue
            if user_input == ":tasks":
                for line in get_task_lines(session):
                    typer.echo(line)
                continue
            if user_input.startswith(":done "):
                task_id = _parse_task_id(user_input[6:])
                if task_id is None:
                    typer.echo("bad task id")
                elif complete_task(session, task_id):
                    typer.echo(f"task #{task_id} done")
                else:
                    typer.echo(f"task #{task_id} not found")
                continue
            if user_input.startswith(":rm "):
                task_id = _parse_task_id(user_input[4:])
                if task_id is None:
                    typer.echo("bad task id")
                elif delete_task(session, task_id):
                    typer.echo(f"task #{task_id} removed")
                else:
                    typer.echo(f"task #{task_id} not found")
                continue
            if user_input.startswith(":add "):
                raw_paths = [part for part in user_input[5:].split() if part]
                stored_files = ingest_files_into_knowledge_base(
                    session,
                    [Path(item) for item in raw_paths],
                )
                typer.echo(f"[knowledge] loaded {len(stored_files)} file(s)")
                continue

            reply = answer_question(session, session_id=session_id, question=user_input)
            typer.echo("")
            typer.echo("agent>")
            typer.echo(reply.reply)
            if reply.matched_chunks:
                typer.echo(f"[context] {', '.join(reply.matched_chunks)}")
            if reply.fallback_used:
                typer.echo("[mode] fallback")
            else:
                typer.echo("[mode] llm")
            typer.echo("")
    finally:
        session.close()


def _parse_task_id(raw_value: str) -> int | None:
    raw_value = raw_value.strip()
    if not raw_value.isdigit():
        return None
    return int(raw_value)
