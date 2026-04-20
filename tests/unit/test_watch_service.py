from pathlib import Path
from threading import Event

from devlens.watch.service import (
    _candidate_files_for_save_mode,
    _changed_files_for_save_mode,
    run_watch_loop,
)


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


def test_changed_files_for_save_mode_tracks_only_new_or_modified(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    target = tmp_path / "sample.py"
    target.write_text("print('v1')\n", encoding="utf-8")
    state: dict[Path, str] = {}

    monkeypatch.setattr(
        "devlens.watch.service.scan_specific_files",
        lambda paths: [type("Scan", (), {"file_path": path}) for path in paths],
    )

    first = _changed_files_for_save_mode(tmp_path, state)
    second = _changed_files_for_save_mode(tmp_path, state)
    target.write_text("print('v2')\n", encoding="utf-8")
    third = _changed_files_for_save_mode(tmp_path, state)

    assert first == [target]
    assert second == []
    assert third == [target]
