from __future__ import annotations

from pathlib import Path
from subprocess import run

from devlens.config import get_settings
from devlens.security.path_guard import ensure_within_root


def get_changed_files(project_root: Path | None = None) -> list[Path]:
    settings = get_settings()
    root = ensure_within_root(
        project_root or settings.resolved_project_root,
        settings.resolved_project_root,
    )
    result = run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    changed_files: list[Path] = []
    for raw_path in result.stdout.splitlines():
        raw_path = raw_path.strip()
        if not raw_path:
            continue
        candidate = root / raw_path
        if candidate.exists() and candidate.is_file():
            changed_files.append(candidate.resolve())
    return changed_files
