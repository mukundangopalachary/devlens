from __future__ import annotations

import ast

from devlens.analysis.static.metrics import collect_static_metrics
from devlens.core.errors import StaticAnalysisError
from devlens.core.schemas import FileAnalysisResult, StaticAnalysisMetrics
from devlens.ingestion.file_scanner import FileScanResult


def analyze_python_file(scan_result: FileScanResult) -> FileAnalysisResult:
    try:
        tree = ast.parse(scan_result.content, filename=str(scan_result.file_path))
    except SyntaxError as exc:
        raise StaticAnalysisError(
            f"Failed to parse {scan_result.relative_path}: {exc.msg}"
        ) from exc

    metrics = collect_static_metrics(scan_result.content, tree)
    issues = _derive_issues(metrics)
    return FileAnalysisResult(
        file_path=scan_result.file_path,
        relative_path=scan_result.relative_path,
        content_hash=scan_result.content_hash,
        metrics=metrics,
        issues=issues,
    )


def _derive_issues(metrics: StaticAnalysisMetrics) -> list[str]:
    issues: list[str] = []
    if metrics.max_nesting_depth >= 4:
        issues.append("Deep nesting detected.")
    if metrics.recursion_detected:
        issues.append("Recursion detected.")
    if metrics.long_function_count > 0:
        issues.append("Long function detected.")
    if metrics.cyclomatic_complexity >= 10:
        issues.append("High cyclomatic complexity.")
    return issues
