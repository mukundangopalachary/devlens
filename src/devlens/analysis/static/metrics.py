from __future__ import annotations

import ast
from typing import cast

from radon.complexity import cc_visit

from devlens.analysis.static.detectors import detect_nesting_depth, detect_recursion
from devlens.core.schemas import StaticAnalysisMetrics


def collect_static_metrics(source: str, tree: ast.AST) -> StaticAnalysisMetrics:
    complexities = cc_visit(source)
    long_function_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node_span = _estimate_node_span(node)
            if node_span >= 30:
                long_function_count += 1

    return StaticAnalysisMetrics(
        function_count=_count_nodes(tree, ast.FunctionDef, ast.AsyncFunctionDef),
        class_count=_count_nodes(tree, ast.ClassDef),
        import_count=_count_nodes(tree, ast.Import, ast.ImportFrom),
        loop_count=_count_nodes(tree, ast.For, ast.AsyncFor, ast.While),
        conditional_count=_count_nodes(tree, ast.If, ast.Match),
        return_count=_count_nodes(tree, ast.Return),
        max_nesting_depth=detect_nesting_depth(tree),
        recursion_detected=detect_recursion(tree),
        cyclomatic_complexity=sum(block.complexity for block in complexities),
        long_function_count=long_function_count,
    )


def _count_nodes(tree: ast.AST, *types: type[ast.AST]) -> int:
    return sum(1 for node in ast.walk(tree) if isinstance(node, types))


def _estimate_node_span(node: ast.AST) -> int:
    start = cast(int | None, getattr(node, "lineno", None))
    end = cast(int | None, getattr(node, "end_lineno", None))
    if start is None or end is None:
        return 0
    return max(end - start + 1, 0)
