from __future__ import annotations

import os
from pathlib import Path
from zipfile import ZipFile

import pytest


@pytest.mark.packaging
def test_cli_installable_and_runnable(tmp_path: Path) -> None:
    _ = tmp_path
    wheel = _latest_wheel(Path("dist"))
    if wheel is None:
        if os.getenv("CI", "").lower() in {"1", "true", "yes"}:
            pytest.fail("CI run missing wheel artifact. Run `uv build --wheel` before pytest.")
        pytest.skip(
            "No built wheel found. "
            "Run `uv build --wheel` before packaging integration test."
        )

    with ZipFile(wheel) as archive:
        names = archive.namelist()
        entry_points = _read_entry_points(archive)

    expected_files = {
        "devlens/main.py",
        "devlens/cli/app.py",
        "devlens/analysis/pipeline.py",
        "devlens/storage/repositories/analyses.py",
        "devlens/skills/scorer.py",
        "devlens/cache/prompt_cache.py",
    }
    missing = sorted(path for path in expected_files if path not in names)
    assert not missing, f"Wheel missing expected modules: {missing}"

    assert "[console_scripts]" in entry_points
    assert "devlens = devlens.main:main" in entry_points


def _latest_wheel(dist_dir: Path) -> Path | None:
    wheels = sorted(dist_dir.glob("devlens-*.whl"))
    if not wheels:
        return None
    return wheels[-1]


def _read_entry_points(archive: ZipFile) -> str:
    for name in archive.namelist():
        if name.endswith(".dist-info/entry_points.txt"):
            return archive.read(name).decode("utf-8")
    return ""
