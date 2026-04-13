from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from sqlalchemy.orm import Session

from devlens.analysis.static.python_ast import analyze_python_file
from devlens.cli.json_contract import emit_json_error, success_response
from devlens.core.schemas import SkillAssessment
from devlens.feedback.tasks import generate_tasks
from devlens.ingestion.file_scanner import scan_specific_files
from devlens.storage.db import SessionLocal
from devlens.storage.repositories.knowledge import (
    list_scheduled_tasks,
    mark_task_done,
    regenerate_tasks_for_file,
    remove_task,
    score_task_priority_from_feedback_text,
    snooze_task,
    update_task_due,
)

LimitOption = Annotated[int, typer.Option("--limit", min=1, max=100, help="Max tasks to list.")]


def tasks_command(
    limit: LimitOption = 20,
    done: int | None = typer.Option(None, "--done", help="Mark task id as done."),
    remove: int | None = typer.Option(None, "--remove", help="Remove task id."),
    due: str | None = typer.Option(
        None,
        "--due",
        help="Set due date using id:days (example: --due 12:3).",
    ),
    snooze: str | None = typer.Option(
        None,
        "--snooze",
        help="Snooze using id:days (example: --snooze 12:2).",
    ),
    regenerate: str | None = typer.Option(
        None,
        "--regenerate",
        help="Regenerate tasks from file analysis.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    operations_requested = sum(
        1 for item in (done, remove, due, snooze, regenerate) if item is not None
    )
    if operations_requested > 1:
        if as_json:
            emit_json_error(
                "tasks",
                "invalid_arguments",
                "Use only one task operation in a single call.",
            )
        else:
            typer.echo("use only one operation: --done/--remove/--due/--snooze/--regenerate")
        raise typer.Exit(code=1)

    session = SessionLocal()
    try:
        generated = 0
        if done is not None:
            success = mark_task_done(session, done)
            if not success:
                session.rollback()
                if as_json:
                    emit_json_error("tasks", "task_not_found", f"Task id {done} not found.")
                else:
                    typer.echo(f"task #{done} not found")
                raise typer.Exit(code=1)
            session.commit()
        elif remove is not None:
            success = remove_task(session, remove)
            if not success:
                session.rollback()
                if as_json:
                    emit_json_error("tasks", "task_not_found", f"Task id {remove} not found.")
                else:
                    typer.echo(f"task #{remove} not found")
                raise typer.Exit(code=1)
            session.commit()
        elif due is not None:
            parsed = _parse_task_days(due)
            if parsed is None:
                if as_json:
                    emit_json_error("tasks", "invalid_arguments", "--due expects id:days")
                typer.echo("--due expects id:days")
                raise typer.Exit(code=1)
            target_id, due_days = parsed
            if due_days <= 0:
                if as_json:
                    emit_json_error("tasks", "invalid_arguments", "--due days must be positive")
                typer.echo("--due days must be positive")
                raise typer.Exit(code=1)
            success = update_task_due(session, target_id, due_days)
            if not success:
                session.rollback()
                if as_json:
                    emit_json_error("tasks", "task_not_found", f"Task id {target_id} not found.")
                typer.echo(f"task #{target_id} not found")
                raise typer.Exit(code=1)
            session.commit()
        elif snooze is not None:
            parsed = _parse_task_days(snooze)
            if parsed is None:
                if as_json:
                    emit_json_error("tasks", "invalid_arguments", "--snooze expects id:days")
                typer.echo("--snooze expects id:days")
                raise typer.Exit(code=1)
            target_id, snooze_days = parsed
            if snooze_days <= 0:
                if as_json:
                    emit_json_error("tasks", "invalid_arguments", "--snooze days must be positive")
                typer.echo("--snooze days must be positive")
                raise typer.Exit(code=1)
            success = snooze_task(session, target_id, snooze_days)
            if not success:
                session.rollback()
                if as_json:
                    emit_json_error("tasks", "task_not_found", f"Task id {target_id} not found.")
                typer.echo(f"task #{target_id} not found")
                raise typer.Exit(code=1)
            session.commit()
        elif regenerate is not None:
            generated = _regenerate_from_file(session, Path(regenerate))
            session.commit()

        tasks = list_scheduled_tasks(session, limit=limit)
    except typer.Exit:
        raise
    except Exception as exc:
        if as_json:
            emit_json_error(
                "tasks",
                "tasks_failed",
                "Tasks command failed.",
                details=str(exc),
            )
        raise
    finally:
        session.close()

    if as_json:
        payload = success_response(
            "tasks",
            {
                "limit": limit,
                "items": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "related_file_path": task.related_file_path,
                        "priority": task.priority,
                        "status": task.status,
                        "due_at": task.due_at.isoformat() if task.due_at else None,
                        "snoozed_until": task.snoozed_until.isoformat()
                        if task.snoozed_until
                        else None,
                        "source_signature": task.source_signature,
                        "priority_score": _priority_score(task.priority, task.description),
                        "created_at": task.created_at.isoformat(),
                    }
                    for task in tasks
                ],
                "generated": generated,
            },
        )
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    if done is not None:
        typer.echo(f"task #{done} done")
    if remove is not None:
        typer.echo(f"task #{remove} removed")
    if regenerate is not None:
        typer.echo(f"regenerated {generated} task(s) from {regenerate}")

    if not tasks:
        typer.echo("No scheduled tasks yet.")
        return

    for task in tasks:
        typer.echo(
            f"#{task.id} | {task.priority.upper()} | {task.status} | "
            f"{task.related_file_path or '-'} | {task.title}"
        )


def _regenerate_from_file(session: Session, file_path: Path) -> int:
    scan_results = scan_specific_files([file_path], include_all_extensions=False)
    if not scan_results:
        return 0
    scan_result = scan_results[0]
    analysis = analyze_python_file(scan_result)
    tasks = generate_tasks(
        analysis.metrics,
        [
            SkillAssessment(
                skill_name="autogen",
                category="analysis",
                score=0.5,
                confidence=0.5,
                reason="task regeneration",
            )
        ],
    )
    return regenerate_tasks_for_file(
        session,
        file_path=str(scan_result.relative_path),
        task_texts=tasks,
    )


def _priority_score(priority: str, description: str) -> float:
    base = {"high": 0.9, "medium": 0.6, "low": 0.3}.get(priority, 0.4)
    recurring = 0.1 if any(term in description.lower() for term in ("again", "recurring")) else 0.0
    inferred = {
        "high": 0.15,
        "medium": 0.05,
        "low": 0.0,
    }[score_task_priority_from_feedback_text(description)]
    return round(min(1.0, base + recurring + inferred), 2)


def _parse_task_days(raw_value: str) -> tuple[int, int] | None:
    if ":" not in raw_value:
        return None
    task_part, days_part = raw_value.split(":", maxsplit=1)
    if not task_part.isdigit() or not days_part.isdigit():
        return None
    return int(task_part), int(days_part)
