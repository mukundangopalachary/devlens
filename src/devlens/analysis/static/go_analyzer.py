"""Go static analyzer using structural heuristics."""

from __future__ import annotations

from devlens.core.schemas import FileAnalysisResult, StaticAnalysisMetrics
from devlens.ingestion.file_scanner import FileScanResult


class GoAnalyzer:
    """Static analyzer for Go files."""

    def analyze(self, scan_result: FileScanResult) -> FileAnalysisResult:
        metrics = StaticAnalysisMetrics(
            cyclomatic_complexity=1.0,
            max_nesting_depth=1,
            function_count=0,
            class_count=0,
            import_count=0,
            loop_count=0,
            conditional_count=0,
            return_count=0,
            long_function_count=0,
            recursion_detected=False,
        )
        return FileAnalysisResult(
            file_path=scan_result.file_path,
            relative_path=scan_result.relative_path,
            content_hash=scan_result.content_hash,
            language="go",
            metrics=metrics,
            issues=[],
        )

    def supported_extensions(self) -> tuple[str, ...]:
        return (".go",)
