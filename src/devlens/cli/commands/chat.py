from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from devlens.chat.service import (
    answer_question,
    build_session_memory_summary,
    complete_task,
    delete_task,
    get_chat_status_line,
    get_task_lines,
    ingest_files_into_knowledge_base,
    set_task_due_days,
    snooze_existing_task,
    start_chat_session,
    stream_answer_question,
)
from devlens.storage.db import SessionLocal

FileArgument = Annotated[list[Path], typer.Argument(resolve_path=True)]


def chat_command(files: FileArgument | None = None) -> None:
    session = SessionLocal()
    try:
        session_id = start_chat_session(session)
        initial_files = [] if files is None else files
        if initial_files:
            stored_files = ingest_files_into_knowledge_base(
                session,
                initial_files,
                session_id=session_id,
            )
            typer.echo(f"[knowledge] loaded {len(stored_files)} file(s)")

        typer.echo("DevLens Chat")
        typer.echo(
            "commands: :add <path>  :tasks [open|done|all]  :done <id>  :rm <id>  "
            ":due <id> <days>  :snooze <id> <days>  :sum  :stream on|off  :help  :exit"
        )
        typer.echo(get_chat_status_line())
        streaming_enabled = False
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
                    ":tasks [open|done|all] show tasks\n"
                    ":done <id> mark task done\n"
                    ":rm <id> remove task\n"
                    ":due <id> <days> move due date forward from now\n"
                    ":snooze <id> <days> hide task until later\n"
                    ":sum print session memory summary\n"
                    ":stream on|off toggle token stream mode\n"
                    ":exit quit chat"
                )
                continue
            if user_input == ":sum":
                typer.echo(build_session_memory_summary(session, session_id=session_id))
                continue
            if user_input.startswith(":stream "):
                mode = user_input[8:].strip().lower()
                if mode in {"on", "off"}:
                    streaming_enabled = mode == "on"
                    typer.echo(f"streaming {'enabled' if streaming_enabled else 'disabled'}")
                else:
                    typer.echo("usage: :stream on|off")
                continue
            if user_input.startswith(":tasks"):
                status = _parse_tasks_status(user_input)
                if status is None:
                    typer.echo("usage: :tasks [open|done|all]")
                    continue
                for line in get_task_lines(session, status=status):
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
            if user_input.startswith(":due "):
                parsed = _parse_task_days_args(user_input[5:])
                if parsed is None:
                    typer.echo("usage: :due <id> <days>")
                else:
                    task_id, days = parsed
                    if set_task_due_days(session, task_id, days):
                        typer.echo(f"task #{task_id} due in {days} day(s)")
                    else:
                        typer.echo(f"task #{task_id} not found")
                continue
            if user_input.startswith(":snooze "):
                parsed = _parse_task_days_args(user_input[8:])
                if parsed is None:
                    typer.echo("usage: :snooze <id> <days>")
                else:
                    task_id, days = parsed
                    if snooze_existing_task(session, task_id, days):
                        typer.echo(f"task #{task_id} snoozed for {days} day(s)")
                    else:
                        typer.echo(f"task #{task_id} not found")
                continue
            if user_input.startswith(":add "):
                raw_paths = [part for part in user_input[5:].split() if part]
                stored_files = ingest_files_into_knowledge_base(
                    session,
                    [Path(item) for item in raw_paths],
                    session_id=session_id,
                )
                typer.echo(f"[knowledge] loaded {len(stored_files)} file(s)")
                continue

            if streaming_enabled:
                typer.echo("")
                typer.echo("agent>")
                _streamed_token_count, reply = stream_answer_question(
                    session,
                    session_id=session_id,
                    question=user_input,
                    on_token=lambda token: typer.echo(token, nl=False),
                )
                typer.echo("")
                rendered = reply.reply
            else:
                reply = answer_question(session, session_id=session_id, question=user_input)
                rendered = reply.reply
                typer.echo("")
                typer.echo("agent>")
                typer.echo(rendered)
            if reply.matched_chunks:
                typer.echo(f"[context] {', '.join(reply.matched_chunks)}")
            if reply.citations:
                typer.echo(f"[citations] {', '.join(reply.citations)}")
            if reply.error_reason:
                typer.echo(f"[error] {reply.error_reason}")
            if reply.error_code:
                typer.echo(f"[error_code] {reply.error_code}")
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


def _parse_task_days_args(raw_value: str) -> tuple[int, int] | None:
    parts = raw_value.split()
    if len(parts) != 2:
        return None
    if not parts[0].isdigit() or not parts[1].isdigit():
        return None
    task_id = int(parts[0])
    days = int(parts[1])
    if days <= 0:
        return None
    return task_id, days


def _parse_tasks_status(user_input: str) -> str | None:
    parts = user_input.split()
    if len(parts) == 1:
        return "open"
    if len(parts) == 2 and parts[1] in {"open", "done", "all"}:
        return parts[1]
    return None
