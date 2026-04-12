from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from devlens.core.schemas import SkillAssessment
from devlens.skills.history import compute_updated_skill_score
from devlens.storage.tables import Skill, SkillHistory


def upsert_skill_assessment(session: Session, assessment: SkillAssessment) -> Skill:
    statement = select(Skill).where(Skill.name == assessment.skill_name)
    skill = session.execute(statement).scalar_one_or_none()

    previous_score = 0.0
    if skill is None:
        skill = Skill(
            name=assessment.skill_name,
            category=assessment.category,
            current_score=assessment.score,
            confidence=assessment.confidence,
        )
        session.add(skill)
        session.flush()
    else:
        previous_score = skill.current_score
        skill.current_score = compute_updated_skill_score(skill.current_score, assessment.score)
        skill.confidence = assessment.confidence
        skill.category = assessment.category
        session.flush()

    history_entry = SkillHistory(
        skill_id=skill.id,
        previous_score=previous_score,
        new_score=skill.current_score,
        delta=skill.current_score - previous_score,
        reason=assessment.reason[:255],
    )
    session.add(history_entry)
    session.flush()
    return skill


def list_skills(session: Session) -> list[Skill]:
    statement = select(Skill).order_by(Skill.current_score.desc(), Skill.name.asc())
    return list(session.execute(statement).scalars())


def get_skill_history(
    session: Session,
    limit: int = 20,
) -> list[tuple[SkillHistory, Skill]]:
    statement = (
        select(SkillHistory, Skill)
        .join(Skill, Skill.id == SkillHistory.skill_id)
        .order_by(SkillHistory.recorded_at.desc())
        .limit(limit)
    )
    rows = session.execute(statement).all()
    return cast(list[tuple[SkillHistory, Skill]], list(rows))
