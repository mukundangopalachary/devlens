from __future__ import annotations

from devlens.core.schemas import StaticAnalysisMetrics


def infer_mistake_patterns(metrics: StaticAnalysisMetrics) -> list[str]:
    mistakes: list[str] = []
    if metrics.max_nesting_depth >= 4:
        mistakes.append("deep_nesting")
    if metrics.long_function_count > 0:
        mistakes.append("long_function")
    if metrics.cyclomatic_complexity >= 10:
        mistakes.append("high_complexity")
    return mistakes
