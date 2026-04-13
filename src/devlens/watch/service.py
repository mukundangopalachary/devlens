from __future__ import annotations

import time
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread

from sqlalchemy.orm import Session

from devlens.analysis.pipeline import run_static_analysis_for_specific_files
from devlens.ingestion.file_scanner import scan_specific_files
from devlens.ingestion.git_diff import get_changed_files


def run_watch_loop(
    session: Session,
    target_path: Path,
    *,
    mode: str,
    interval_seconds: float,
    max_queue_size: int = 128,
    max_batch_size: int = 32,
    stop_event: Event | None = None,
) -> dict[str, int]:
    stats = {
        "loops": 0,
        "queued": 0,
        "analyzed": 0,
        "errors": 0,
        "skipped": 0,
    }
    event = stop_event or Event()
    queue: Queue[Path] = Queue(maxsize=max_queue_size)
    seen_paths: set[Path] = set()

    worker = Thread(
        target=_worker_loop,
        args=(session, queue, seen_paths, stats, max_batch_size, event),
        daemon=True,
    )
    worker.start()

    while not event.is_set():
        stats["loops"] += 1
        candidate_paths = _collect_paths(target_path=target_path, mode=mode)
        for path in candidate_paths:
            if path in seen_paths:
                continue
            if queue.full():
                stats["skipped"] += 1
                continue
            queue.put(path)
            seen_paths.add(path)
            stats["queued"] += 1
        time.sleep(interval_seconds)

    worker.join(timeout=max(interval_seconds * 2, 1.0))
    return stats


def _worker_loop(
    session: Session,
    queue: Queue[Path],
    seen_paths: set[Path],
    stats: dict[str, int],
    max_batch_size: int,
    stop_event: Event,
) -> None:
    while not stop_event.is_set() or not queue.empty():
        batch: list[Path] = []
        try:
            first = queue.get(timeout=0.2)
            batch.append(first)
        except Empty:
            continue

        while len(batch) < max_batch_size and not queue.empty():
            try:
                batch.append(queue.get_nowait())
            except Empty:
                break

        safe_batch = [item for item in batch if item.exists() and item.is_file()]
        if not safe_batch:
            for item in batch:
                seen_paths.discard(item)
            continue

        try:
            summary, _ = run_static_analysis_for_specific_files(safe_batch, session)
            stats["analyzed"] += summary.files_analyzed
        except Exception:
            stats["errors"] += 1
            session.rollback()
        finally:
            for item in batch:
                seen_paths.discard(item)


def _collect_paths(target_path: Path, mode: str) -> list[Path]:
    if mode == "git":
        return get_changed_files(target_path)
    if mode == "save":
        scan_results = scan_specific_files(_candidate_files_for_save_mode(target_path))
        return [result.file_path for result in scan_results]
    return []


def _candidate_files_for_save_mode(target_path: Path) -> list[Path]:
    if target_path.is_file():
        return [target_path]
    if not target_path.exists() or not target_path.is_dir():
        return []
    return [path for path in sorted(target_path.rglob("*")) if path.is_file()]
