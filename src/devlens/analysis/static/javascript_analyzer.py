"""JavaScript/TypeScript static analyzer using structural heuristics."""

from __future__ import annotations

import re

from devlens.core.schemas import FileAnalysisResult, StaticAnalysisMetrics
from devlens.ingestion.file_scanner import FileScanResult


class JavaScriptAnalyzer:
    """Static analyzer for JS/TS files."""

    def analyze(self, scan_result: FileScanResult) -> FileAnalysisResult:
        content = scan_result.content
        
        # Simple regex heuristics to avoid heavy AST parsing
        functions = len(re.findall(r"\bfunction\b|=>", content))
        classes = len(re.findall(r"\bclass\s+\w+", content))
        imports = len(re.findall(r"\bimport\b|\brequire\s*\(", content))
        loops = len(re.findall(r"\bfor\s*\(|\bwhile\s*\(|\.forEach\s*\(|\.map\s*\(", content))
        conditionals = len(re.findall(r"\bif\s*\(|\bswitch\s*\(", content))
        returns = len(re.findall(r"\breturn\b", content))
        
        # Estimate cyclomatic complexity (base 1 + conditionals + loops)
        complexity = float(1 + conditionals + loops)

        metrics = StaticAnalysisMetrics(
            cyclomatic_complexity=complexity,
            max_nesting_depth=1,  # Not easily determinable via regex
            function_count=functions,
            class_count=classes,
            import_count=imports,
            loop_count=loops,
            conditional_count=conditionals,
            return_count=returns,
            long_function_count=0,
            recursion_detected=False,
        )
        
        return FileAnalysisResult(
            file_path=scan_result.file_path,
            relative_path=scan_result.relative_path,
            content_hash=scan_result.content_hash,
            language="javascript",
            metrics=metrics,
            issues=[],
        )

    def supported_extensions(self) -> tuple[str, ...]:
        return (".js", ".ts", ".jsx", ".tsx")
