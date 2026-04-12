from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from devlens.storage.tables import AnalysisResult


def create_analysis_result(
    session: Session,
    submission_id: int,
    language: str,
    structural_json: str,
    llm_json: str,
    complexity_score: float,
    issues_json: str,
    analysis_version: str,
) -> AnalysisResult:
    analysis_result = AnalysisResult(
        submission_id=submission_id,
        language=language,
        structural_json=structural_json,
        llm_json=llm_json,
        complexity_score=complexity_score,
        issues_json=issues_json,
        analysis_version=analysis_version,
    )
    session.add(analysis_result)
    session.flush()
    return analysis_result


def get_latest_analysis_for_submission(
    session: Session,
    submission_id: int,
) -> AnalysisResult | None:
    statement = (
        select(AnalysisResult)
        .where(AnalysisResult.submission_id == submission_id)
        .order_by(AnalysisResult.created_at.desc())
    )
    return session.execute(statement).scalars().first()
