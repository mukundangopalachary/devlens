from pathlib import Path
from threading import Event

from devlens.watch.service import _candidate_files_for_save_mode, run_watch_loop


class _FakeSession:
    def rollback(self) -> None:
        return None


def test_candidate_files_for_save_mode_empty_on_missing_path() -> None:
    files = _candidate_files_for_save_mode(Path("/tmp/definitely-missing-devlens-watch-path"))
    assert files == []


def test_run_watch_loop_returns_stats_when_stopped_immediately() -> None:
    stop_event = Event()
    stop_event.set()
    stats = run_watch_loop(
        _FakeSession(),
        Path("."),
        mode="git",
        interval_seconds=0.2,
        stop_event=stop_event,
    )
    assert set(stats.keys()) == {"loops", "queued", "analyzed", "errors", "skipped"}
