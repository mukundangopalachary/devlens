from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from devlens.storage.tables import AnalysisResult, CodeSubmission, FeedbackItem


def create_feedback_item(
    session: Session,
    analysis_result_id: int,
    kind: str,
    content: str,
    difficulty: str | None = None,
    related_skill: str | None = None,
) -> FeedbackItem:
    item = FeedbackItem(
        analysis_result_id=analysis_result_id,
        kind=kind,
        content=content,
        difficulty=difficulty,
        related_skill=related_skill,
    )
    session.add(item)
    session.flush()
    return item


def list_latest_feedback(
    session: Session,
    limit: int = 10,
) -> list[tuple[FeedbackItem, AnalysisResult, CodeSubmission]]:
    statement = (
        select(FeedbackItem, AnalysisResult, CodeSubmission)
        .join(AnalysisResult, AnalysisResult.id == FeedbackItem.analysis_result_id)
        .join(CodeSubmission, CodeSubmission.id == AnalysisResult.submission_id)
        .order_by(AnalysisResult.created_at.desc(), FeedbackItem.id.asc())
        .limit(limit)
    )
    rows = session.execute(statement).all()
    return cast(list[tuple[FeedbackItem, AnalysisResult, CodeSubmission]], list(rows))
