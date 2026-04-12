from devlens.core.schemas import LLMAnalysisResult, StaticAnalysisMetrics
from devlens.skills.scorer import score_skills


def test_score_skills_returns_recursion_skill() -> None:
    metrics = StaticAnalysisMetrics(
        function_count=1,
        loop_count=1,
        conditional_count=1,
        max_nesting_depth=2,
        recursion_detected=True,
        cyclomatic_complexity=5,
    )
    llm_result = LLMAnalysisResult(
        patterns=["recursion"],
        optimization_assessment="Optimization is acceptable.",
        critique="Looks fine.",
        confidence=0.7,
    )

    assessments = score_skills(metrics, llm_result)

    assert any(item.skill_name == "Recursion" for item in assessments)
