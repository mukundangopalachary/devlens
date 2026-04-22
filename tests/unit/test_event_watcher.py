"""Tests for the event-driven filesystem watcher."""

from __future__ import annotations

from pathlib import Path
from queue import Queue

from devlens.watch.event_watcher import DebouncedHandler, watchdog_available


def test_watchdog_available() -> None:
    assert watchdog_available() is True


def test_debounced_handler_filters_ignored_dirs() -> None:
    q: Queue[Path] = Queue()
    handler = DebouncedHandler(
        output_queue=q,
        debounce_seconds=0.1,
        allowed_extensions=(".py",),
    )
    try:
        # Simulate event from ignored dir
        from unittest.mock import MagicMock

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/project/.venv/lib/module.py"
        handler._handle(event)
        assert len(handler._pending) == 0

        # Simulate event from valid path
        event2 = MagicMock()
        event2.is_directory = False
        event2.src_path = "/project/src/main.py"
        handler._handle(event2)
        assert len(handler._pending) == 1
    finally:
        handler.stop()


def test_debounced_handler_filters_extensions() -> None:
    q: Queue[Path] = Queue()
    handler = DebouncedHandler(
        output_queue=q,
        debounce_seconds=0.1,
        allowed_extensions=(".py",),
    )
    try:
        from unittest.mock import MagicMock

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/project/src/readme.md"
        handler._handle(event)
        assert len(handler._pending) == 0
    finally:
        handler.stop()


def test_debounced_handler_ignores_directories() -> None:
    q: Queue[Path] = Queue()
    handler = DebouncedHandler(
        output_queue=q,
        debounce_seconds=0.1,
        allowed_extensions=(".py",),
    )
    try:
        from unittest.mock import MagicMock

        event = MagicMock()
        event.is_directory = True
        event.src_path = "/project/src/"
        handler._handle(event)
        assert len(handler._pending) == 0
    finally:
        handler.stop()
