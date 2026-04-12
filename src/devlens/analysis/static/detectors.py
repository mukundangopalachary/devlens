from __future__ import annotations

import ast


def detect_recursion(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _function_is_recursive(
            node
        ):
            return True
    return False


def _function_is_recursive(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for inner in ast.walk(node):
        if (
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Name)
            and inner.func.id == node.name
        ):
            return True
    return False


def detect_nesting_depth(tree: ast.AST) -> int:
    max_depth = 0

    def visit(node: ast.AST, depth: int) -> None:
        nonlocal max_depth
        max_depth = max(max_depth, depth)
        next_depth = depth + 1 if isinstance(node, NESTED_BLOCK_NODES) else depth
        for child in ast.iter_child_nodes(node):
            visit(child, next_depth)

    visit(tree, 0)
    return max_depth


NESTED_BLOCK_NODES = (
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.If,
    ast.Try,
    ast.With,
    ast.AsyncWith,
    ast.Match,
)
