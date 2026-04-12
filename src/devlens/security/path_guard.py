from __future__ import annotations

from pathlib import Path


def ensure_within_root(candidate: Path, root: Path) -> Path:
    resolved_root = root.expanduser().resolve()
    resolved_candidate = candidate.expanduser().resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(
            f"Path '{resolved_candidate}' is outside allowed root '{resolved_root}'."
        ) from exc
    return resolved_candidate
