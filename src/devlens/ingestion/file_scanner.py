from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from devlens.config import get_settings
from devlens.security.path_guard import ensure_within_root

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "alembic",
    "build",
    "dist",
}


@dataclass(frozen=True)
class FileScanResult:
    project_root: Path
    file_path: Path
    relative_path: Path
    content_hash: str
    size_bytes: int
    content: str
    source_type: str = "filesystem"


def scan_python_files(target_path: Path) -> list[FileScanResult]:
    settings = get_settings()
    project_root = settings.resolved_project_root
    safe_target = ensure_within_root(target_path, project_root)

    files = _candidate_files(safe_target, settings.allowed_extensions)
    return build_scan_results(files=files, project_root=project_root)


def scan_specific_files(file_paths: list[Path]) -> list[FileScanResult]:
    settings = get_settings()
    project_root = settings.resolved_project_root
    safe_files = [
        ensure_within_root(file_path, project_root)
        for file_path in file_paths
        if file_path.suffix in settings.allowed_extensions and not _is_ignored(file_path)
    ]
    return build_scan_results(files=safe_files, project_root=project_root)


def build_scan_results(files: list[Path], project_root: Path) -> list[FileScanResult]:
    scan_results: list[FileScanResult] = []
    for file_path in files:
        result = _build_scan_result(file_path=file_path, project_root=project_root)
        if result is not None:
            scan_results.append(result)
    return scan_results


def _candidate_files(target_path: Path, allowed_extensions: tuple[str, ...]) -> list[Path]:
    if target_path.is_file():
        return [target_path] if target_path.suffix in allowed_extensions else []

    return sorted(
        file_path
        for file_path in target_path.rglob("*")
        if file_path.is_file()
        and file_path.suffix in allowed_extensions
        and not _is_ignored(file_path)
    )


def _build_scan_result(file_path: Path, project_root: Path) -> FileScanResult | None:
    settings = get_settings()
    stat = file_path.stat()
    if stat.st_size > settings.max_file_size_bytes:
        return None

    content = file_path.read_text(encoding="utf-8")
    return FileScanResult(
        project_root=project_root,
        file_path=file_path,
        relative_path=file_path.relative_to(project_root),
        content_hash=sha256(content.encode("utf-8")).hexdigest(),
        size_bytes=stat.st_size,
        content=content,
    )


def _is_ignored(file_path: Path) -> bool:
    return any(part in IGNORED_DIRECTORY_NAMES for part in file_path.parts)
