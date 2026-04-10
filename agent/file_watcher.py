"""
agent/file_watcher.py — Watchdog-based File System Monitor

Watches critical directories for create/modify/delete/move events
and injects file_event dicts into the given SystemSnapshot queue
via a shared list that the MonitoringAgent reads each cycle.
"""

import logging
import threading
from pathlib import Path
from typing import Callable

from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileDeletedEvent,
    FileMovedEvent,
)

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import WATCHED_PATHS

logger = logging.getLogger(__name__)


class _CyberEventHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[dict], None]):
        super().__init__()
        self._cb = callback

    def _emit(self, event_type: str, src: str, dest: str = ""):
        evt = {"type": event_type, "src": src, "dest": dest}
        logger.debug("File event: %s", evt)
        self._cb(evt)

    def on_created(self, event):
        if not event.is_directory:
            self._emit("create", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._emit("modify", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._emit("delete", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._emit("move", event.src_path, event.dest_path)


class FileWatcher(threading.Thread):
    """
    Starts a watchdog Observer for all WATCHED_PATHS.
    Events are accumulated in self.pending_events (thread-safe list via lock).
    The MonitoringAgent drains this list each cycle.
    """

    daemon = True

    def __init__(self):
        super().__init__(name="FileWatcher")
        self._pending: list[dict] = []
        self._lock = threading.Lock()
        self._observer = Observer()
        self._stop_event = threading.Event()

        handler = _CyberEventHandler(callback=self._on_event)
        for path_str in WATCHED_PATHS:
            p = Path(path_str)
            if p.exists():
                try:
                    self._observer.schedule(handler, str(p), recursive=True)
                    logger.info("Watching: %s", p)
                except Exception as e:
                    logger.warning("Cannot watch %s: %s", p, e)
            else:
                logger.debug("Skipping non-existent watch path: %s", p)

    def _on_event(self, evt: dict):
        with self._lock:
            self._pending.append(evt)

    def drain(self) -> list[dict]:
        """Atomically drain and return all pending file events."""
        with self._lock:
            events, self._pending = self._pending, []
        return events

    def run(self):
        logger.info("FileWatcher started")
        self._observer.start()
        self._stop_event.wait()
        self._observer.stop()
        self._observer.join()
        logger.info("FileWatcher stopped")

    def stop(self):
        self._stop_event.set()


__all__ = ["FileWatcher"]
