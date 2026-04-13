from pathlib import Path

from devlens.chat.service import _expand_add_paths


def test_expand_add_paths_expands_directory() -> None:
    files = _expand_add_paths([Path("src/devlens/analysis")])
    assert any(str(item).endswith("pipeline.py") for item in files)


def test_expand_add_paths_handles_root_marker() -> None:
    files = _expand_add_paths([Path("@.")])
    assert any(str(item).endswith("src/devlens/main.py") for item in files)
