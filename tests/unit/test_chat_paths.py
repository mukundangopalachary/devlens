from pathlib import Path

from devlens.chat.service import _expand_add_paths, _filter_tasks
from devlens.cli.commands.chat import _parse_task_days_args, _parse_tasks_status


def test_expand_add_paths_expands_directory() -> None:
    files = _expand_add_paths([Path("src/devlens/analysis")])
    assert any(str(item).endswith("pipeline.py") for item in files)


def test_expand_add_paths_handles_root_marker() -> None:
    files = _expand_add_paths([Path("@.")])
    assert any(str(item).endswith("src/devlens/main.py") for item in files)


def test_parse_task_days_args_accepts_positive_values() -> None:
    assert _parse_task_days_args("12 3") == (12, 3)


def test_parse_task_days_args_rejects_invalid_values() -> None:
    assert _parse_task_days_args("12") is None
    assert _parse_task_days_args("x 3") is None
    assert _parse_task_days_args("12 0") is None


def test_parse_tasks_status_defaults_to_open() -> None:
    assert _parse_tasks_status(":tasks") == "open"
    assert _parse_tasks_status(":tasks done") == "done"
    assert _parse_tasks_status(":tasks all") == "all"
    assert _parse_tasks_status(":tasks later") is None


class _Task:
    def __init__(self, status: str) -> None:
        self.status = status


def test_filter_tasks_respects_status_mode() -> None:
    tasks = [_Task("open"), _Task("done"), _Task("queued")]
    assert len(_filter_tasks(tasks, status="all")) == 3
    assert len(_filter_tasks(tasks, status="done")) == 1
    assert len(_filter_tasks(tasks, status="open")) == 2
