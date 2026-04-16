from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile


def test_built_wheel_contains_cache_package() -> None:
    dist_dir = Path("dist")
    wheels = sorted(dist_dir.glob("devlens-*.whl"))
    if not wheels:
        # Build artifact not present in normal unit test runs.
        # CI/build pipeline should run this test after `uv build --wheel`.
        return

    wheel = wheels[-1]
    with ZipFile(wheel) as archive:
        names = archive.namelist()

    assert "devlens/cache/__init__.py" in names
    assert "devlens/cache/prompt_cache.py" in names
    assert "devlens/cache/result_cache.py" in names
