from __future__ import annotations

from devlens.core.schemas import LLMAnalysisResult, SkillAssessment, StaticAnalysisMetrics


def score_skills(
    metrics: StaticAnalysisMetrics,
    llm_result: LLMAnalysisResult,
) -> list[SkillAssessment]:
    assessments: list[SkillAssessment] = []

    if metrics.recursion_detected:
        assessments.append(
            SkillAssessment(
                skill_name="Recursion",
                category="DSA",
                score=0.75,
                confidence=0.7,
                reason="Recursive call detected in function body.",
            )
        )

    complexity_penalty = min(metrics.cyclomatic_complexity / 15.0, 0.4)
    modularity_score = max(
        0.2,
        min(1.0, 0.6 + (metrics.function_count * 0.05) - complexity_penalty),
    )
    assessments.append(
        SkillAssessment(
            skill_name="Modularity",
            category="Engineering",
            score=round(modularity_score, 2),
            confidence=0.6,
            reason="Derived from function count and control-flow complexity.",
        )
    )

    optimization_score = (
        0.8 if "optimization" in llm_result.optimization_assessment.lower() else 0.55
    )
    if metrics.cyclomatic_complexity >= 10:
        optimization_score -= 0.15
    assessments.append(
        SkillAssessment(
            skill_name="Optimization Thinking",
            category="Engineering",
            score=round(max(0.2, optimization_score), 2),
            confidence=max(llm_result.confidence, 0.4),
            reason=llm_result.optimization_assessment or "Based on structural complexity signals.",
        )
    )

    readability_score = 0.75
    if metrics.long_function_count > 0 or metrics.max_nesting_depth >= 4:
        readability_score -= 0.2
    assessments.append(
        SkillAssessment(
            skill_name="Code Readability",
            category="Engineering",
            score=round(max(0.2, readability_score), 2),
            confidence=0.6,
            reason="Derived from nesting depth and long-function signals.",
        )
    )

    if metrics.conditional_count > 0:
        assessments.append(
            SkillAssessment(
                skill_name="Edge Case Handling",
                category="Engineering",
                score=0.65,
                confidence=0.5,
                reason="Conditional logic suggests edge-case consideration.",
            )
        )

    return assessments
