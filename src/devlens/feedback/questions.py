from __future__ import annotations

from devlens.core.schemas import SkillAssessment, StaticAnalysisMetrics


def generate_questions(
    metrics: StaticAnalysisMetrics,
    skill_assessments: list[SkillAssessment],
) -> list[str]:
    questions: list[str] = []
    if metrics.recursion_detected:
        questions.append(
            "What is base case for recursive branch, and how do you prove termination?"
        )
    if metrics.max_nesting_depth >= 3:
        questions.append("How can you reduce nesting depth without changing behavior?")
    weak_skills = [skill for skill in skill_assessments if skill.score < 0.6]
    if weak_skills:
        questions.append(
            f"What refactor would most improve {weak_skills[0].skill_name.lower()} in this file?"
        )
    return questions[:3]
