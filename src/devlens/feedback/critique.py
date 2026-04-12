from __future__ import annotations

from devlens.core.schemas import LLMAnalysisResult, StaticAnalysisMetrics


def build_critique(
    metrics: StaticAnalysisMetrics,
    llm_result: LLMAnalysisResult,
    issues: list[str],
) -> str:
    if llm_result.critique:
        return llm_result.critique

    if issues:
        return f"Static critique: {' '.join(issues)}"

    if metrics.function_count == 0:
        return "Static critique: file has no executable functions, so skill signal is limited."

    return "Static critique: structure is valid, but deeper semantic review is still pending."
