from __future__ import annotations

from devlens.core.schemas import SkillAssessment, StaticAnalysisMetrics


def generate_tasks(
    metrics: StaticAnalysisMetrics,
    skill_assessments: list[SkillAssessment],
) -> list[str]:
    tasks: list[str] = []
    if metrics.max_nesting_depth >= 3:
        tasks.append("Refactor one deeply nested branch into guard clauses or helper functions.")
    if metrics.long_function_count > 0:
        tasks.append("Split one long function into smaller single-purpose helpers.")
    weak_skills = [skill for skill in skill_assessments if skill.score < 0.6]
    if weak_skills:
        tasks.append(
            f"Write a revised version of this file focused on improving "
            f"{weak_skills[0].skill_name}."
        )
    if not tasks:
        tasks.append(
            "Document tradeoffs in current implementation and note one improvement "
            "you would defer."
        )
    return tasks[:3]
