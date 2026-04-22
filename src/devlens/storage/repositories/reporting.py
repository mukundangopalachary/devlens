from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from devlens.storage.tables import AnalysisResult, CodeSubmission, FeedbackItem, ScheduledTask


def build_report_snapshot(
    session: Session,
    *,
    days: int,
    limit: int,
) -> dict[str, object]:
    now = datetime.now(UTC)
    since = now - timedelta(days=days)

    analyses_total = _count_analyses_since(session, since)
    analyses_by_day = _analyses_by_day(session, since)
    recurring_issue_themes = _recurring_issue_themes(session, since, limit)
    recurring_task_themes = _recurring_task_themes(session, since, limit)
    task_summary = _task_summary(session, since)
    top_files = _top_touched_files(session, since, limit)

    return {
        "window_days": days,
        "from": since.isoformat(),
        "to": now.isoformat(),
        "analyses_total": analyses_total,
        "analyses_by_day": analyses_by_day,
        "recurring_issue_themes": recurring_issue_themes,
        "recurring_task_themes": recurring_task_themes,
        "task_summary": task_summary,
        "top_touched_files": top_files,
    }


def _count_analyses_since(session: Session, since: datetime) -> int:
    statement = (
        select(func.count())
        .select_from(AnalysisResult)
        .where(AnalysisResult.created_at >= since)
    )
    value = session.execute(statement).scalar_one()
    return int(value)


def _analyses_by_day(session: Session, since: datetime) -> list[dict[str, object]]:
    statement = (
        select(func.date(AnalysisResult.created_at), func.count())
        .where(AnalysisResult.created_at >= since)
        .group_by(func.date(AnalysisResult.created_at))
        .order_by(func.date(AnalysisResult.created_at).asc())
    )
    rows = session.execute(statement).all()
    return [{"date": str(day), "count": int(count)} for day, count in rows]


def _recurring_issue_themes(
    session: Session,
    since: datetime,
    limit: int,
) -> list[dict[str, object]]:
    statement = select(AnalysisResult.issues_json).where(AnalysisResult.created_at >= since)
    rows = session.execute(statement).all()
    counter: Counter[str] = Counter()
    for (issues_json,) in rows:
        counter.update(_extract_issue_tokens(str(issues_json)))
    return [{"theme": theme, "count": count} for theme, count in counter.most_common(limit)]


def _recurring_task_themes(
    session: Session,
    since: datetime,
    limit: int,
) -> list[dict[str, object]]:
    statement = (
        select(FeedbackItem.content)
        .join(AnalysisResult, AnalysisResult.id == FeedbackItem.analysis_result_id)
        .where(AnalysisResult.created_at >= since, FeedbackItem.kind == "task")
    )
    rows = session.execute(statement).all()
    counter: Counter[str] = Counter()
    for (content,) in rows:
        counter.update(_extract_text_themes(str(content)))
    return [{"theme": theme, "count": count} for theme, count in counter.most_common(limit)]


def _task_summary(session: Session, since: datetime) -> dict[str, object]:
    statement = select(ScheduledTask).where(ScheduledTask.created_at >= since)
    rows = list(cast(list[ScheduledTask], session.execute(statement).scalars().all()))
    total = len(rows)
    done = sum(1 for task in rows if task.status == "done")
    pending = sum(1 for task in rows if task.status == "pending")
    completion_rate = 0.0 if total == 0 else round(done / total, 3)
    return {
        "total": total,
        "done": done,
        "pending": pending,
        "completion_rate": completion_rate,
    }


def _top_touched_files(
    session: Session,
    since: datetime,
    limit: int,
) -> list[dict[str, object]]:
    statement = (
        select(CodeSubmission.file_path, func.count())
        .join(AnalysisResult, AnalysisResult.submission_id == CodeSubmission.id)
        .where(AnalysisResult.created_at >= since)
        .group_by(CodeSubmission.file_path)
        .order_by(func.count().desc(), CodeSubmission.file_path.asc())
        .limit(limit)
    )
    rows = session.execute(statement).all()
    return [{"file_path": str(path), "analysis_count": int(count)} for path, count in rows]


def _extract_issue_tokens(raw_issues_json: str) -> list[str]:
    try:
        parsed = json.loads(raw_issues_json)
    except Exception:
        return []

    if isinstance(parsed, list):
        values = [str(item) for item in parsed]
    elif isinstance(parsed, dict):
        issue_values = parsed.get("issues", [])
        if isinstance(issue_values, list):
            values = [str(item) for item in issue_values]
        else:
            values = []
    else:
        values = []

    themes: list[str] = []
    for value in values:
        themes.extend(_extract_text_themes(value))
    return themes


def _extract_text_themes(text: str) -> list[str]:
    normalized = text.lower()
    keyword_groups = {
        "complexity": ("complex", "nest", "branch", "cyclomatic"),
        "function_size": ("long function", "split", "extract"),
        "naming": ("name", "naming", "identifier"),
        "error_handling": ("error", "exception", "try", "catch"),
        "duplication": ("duplicate", "duplication", "repeat"),
        "style": ("style", "format", "readability"),
        "tests": ("test", "coverage", "assert"),
    }
    matches = [
        group
        for group, words in keyword_groups.items()
        if any(word in normalized for word in words)
    ]
    if matches:
        return matches
    fallback = normalized.strip()
    if not fallback:
        return []
    return [fallback[:48]]
