"""Event-driven filesystem watcher with debounce.

Uses watchdog for real-time file change detection.
Falls back gracefully if watchdog is unavailable.
"""

from __future__ import annotations

import time
from pathlib import Path
from queue import Queue
from threading import Event, Lock, Thread

from devlens.config import get_settings
from devlens.ingestion.file_scanner import IGNORED_DIRECTORY_NAMES

WATCHDOG_AVAILABLE = True
try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    WATCHDOG_AVAILABLE = False


def watchdog_available() -> bool:
    return WATCHDOG_AVAILABLE


class DebouncedHandler(FileSystemEventHandler):
    """Collects filesystem events and debounces them."""

    def __init__(
        self,
        output_queue: Queue[Path],
        debounce_seconds: float,
        allowed_extensions: tuple[str, ...],
    ) -> None:
        super().__init__()
        self._output_queue = output_queue
        self._debounce_seconds = debounce_seconds
        self._allowed_extensions = allowed_extensions
        self._pending: dict[str, float] = {}
        self._lock = Lock()
        self._flush_thread = Thread(target=self._flush_loop, daemon=True)
        self._stop = Event()
        self._flush_thread.start()

    def stop(self) -> None:
        self._stop.set()

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def _handle(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(str(event.src_path))
        if not self._is_allowed(path):
            return
        with self._lock:
            self._pending[str(path)] = time.monotonic()

    def _is_allowed(self, path: Path) -> bool:
        if any(part in IGNORED_DIRECTORY_NAMES for part in path.parts):
            return False
        if path.suffix not in self._allowed_extensions:
            return False
        return True

    def _flush_loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(self._debounce_seconds)
            now = time.monotonic()
            to_emit: list[str] = []
            with self._lock:
                for path_str, ts in list(self._pending.items()):
                    if now - ts >= self._debounce_seconds:
                        to_emit.append(path_str)
                for path_str in to_emit:
                    del self._pending[path_str]
            for path_str in to_emit:
                p = Path(path_str)
                if p.exists() and p.is_file():
                    try:
                        self._output_queue.put_nowait(p)
                    except Exception:
                        pass


def run_event_watch(
    target_path: Path,
    output_queue: Queue[Path],
    stop_event: Event,
    *,
    debounce_seconds: float = 0.5,
) -> None:
    """Run event-driven watcher. Blocks until stop_event is set."""
    if not WATCHDOG_AVAILABLE:
        return

    settings = get_settings()
    handler = DebouncedHandler(
        output_queue=output_queue,
        debounce_seconds=debounce_seconds,
        allowed_extensions=settings.allowed_extensions,
    )
    observer = Observer()
    observer.schedule(handler, str(target_path), recursive=True)
    observer.start()

    try:
        while not stop_event.is_set():
            time.sleep(0.2)
    finally:
        handler.stop()
        observer.stop()
        observer.join(timeout=2.0)
