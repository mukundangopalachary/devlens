"""Language analyzer registry.

Dispatches file analysis to language-specific analyzers based on
file extension. Falls back to a generic analyzer for unknown types.
"""

from __future__ import annotations

from typing import Protocol

from devlens.core.schemas import FileAnalysisResult
from devlens.ingestion.file_scanner import FileScanResult


class LanguageAnalyzer(Protocol):
    """Protocol for language-specific static analyzers."""

    def analyze(self, scan_result: FileScanResult) -> FileAnalysisResult: ...

    def supported_extensions(self) -> tuple[str, ...]: ...


class AnalyzerRegistry:
    """Maps file extensions to language analyzers."""

    def __init__(self) -> None:
        self._analyzers: dict[str, LanguageAnalyzer] = {}
        self._generic: LanguageAnalyzer | None = None

    def register(self, analyzer: LanguageAnalyzer) -> None:
        for ext in analyzer.supported_extensions():
            self._analyzers[ext] = analyzer

    def set_generic(self, analyzer: LanguageAnalyzer) -> None:
        self._generic = analyzer

    def get_analyzer(self, extension: str) -> LanguageAnalyzer:
        analyzer = self._analyzers.get(extension)
        if analyzer is not None:
            return analyzer
        if self._generic is not None:
            return self._generic
        raise ValueError(f"No analyzer registered for extension: {extension}")


_REGISTRY: AnalyzerRegistry | None = None


def get_registry() -> AnalyzerRegistry:
    """Get or create the global analyzer registry."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_default_registry()
    return _REGISTRY


def _build_default_registry() -> AnalyzerRegistry:
    from devlens.analysis.static.generic_analyzer import GenericAnalyzer
    from devlens.analysis.static.go_analyzer import GoAnalyzer
    from devlens.analysis.static.java_analyzer import JavaAnalyzer
    from devlens.analysis.static.javascript_analyzer import JavaScriptAnalyzer
    from devlens.analysis.static.python_ast import PythonAnalyzer

    registry = AnalyzerRegistry()
    registry.register(PythonAnalyzer())
    registry.register(JavaScriptAnalyzer())
    registry.register(GoAnalyzer())
    registry.register(JavaAnalyzer())
    registry.set_generic(GenericAnalyzer())
    return registry
