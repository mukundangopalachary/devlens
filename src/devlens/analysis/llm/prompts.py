from __future__ import annotations

from textwrap import dedent

from devlens.core.schemas import StaticAnalysisMetrics


def build_analysis_prompt(source: str, metrics: StaticAnalysisMetrics, issues: list[str]) -> str:
    trimmed_source = source[:4000]
    issue_summary = ", ".join(issues) if issues else "None"
    return dedent(
        f"""
        You analyze Python code for developer skill signals.
        Return strict JSON with keys:
        patterns (array of strings),
        optimization_assessment (string),
        critique (string),
        confidence (number from 0 to 1).

        Static metrics:
        - function_count: {metrics.function_count}
        - class_count: {metrics.class_count}
        - loop_count: {metrics.loop_count}
        - conditional_count: {metrics.conditional_count}
        - max_nesting_depth: {metrics.max_nesting_depth}
        - recursion_detected: {metrics.recursion_detected}
        - cyclomatic_complexity: {metrics.cyclomatic_complexity}
        - long_function_count: {metrics.long_function_count}
        - known_issues: {issue_summary}

        Code:
        ```python
        {trimmed_source}
        ```
        """
    ).strip()
