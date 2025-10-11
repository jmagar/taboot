"""File system watcher for real-time session monitoring.

This module implements SessionsWatcher using the watchdog library for monitoring
AI coding assistant session directories and triggering ingestion on file changes.

Features:
    - Cross-platform file system monitoring (inotify, FSEvents, etc.)
    - Recursive directory watching for .jsonl files
    - Event debouncing to avoid duplicate processing
    - Filters for JSONL files only, ignores temporary files
    - Thread-safe callback execution

Architecture:
    - Uses watchdog.observers.Observer for file system events
    - Custom FileSystemEventHandler filters and debounces events
    - Calls registered callback with file path on modification
    - Graceful start/stop lifecycle management

Debouncing:
    - Multiple modification events fire for single file write
    - Uses threading.Timer to delay callback by 100ms
    - Resets timer if same file modified again within window
    - Prevents duplicate ingestion of same content

Usage:
    def on_file_modified(file_path: Path) -> None:
        print(f"File changed: {file_path}")

    watcher = SessionsWatcher(
        watch_paths=[Path("~/.claude/projects"), Path("~/.codex/sessions")],
        event_callback=on_file_modified
    )
    watcher.start()
    # ... do work ...
    watcher.stop()
"""

import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import (  # type: ignore[import-not-found]
    FileModifiedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer  # type: ignore[import-not-found]


class _DebouncedEventHandler(FileSystemEventHandler):  # type: ignore[misc]
    """Custom event handler that filters and debounces .jsonl file modifications.

    Attributes:
        event_callback: Function to call when a JSONL file is modified
        debounce_timers: Dictionary tracking active debounce timers per file path
        debounce_lock: Thread lock for safe timer access
    """

    def __init__(self, event_callback: Callable[[Path], None]) -> None:
        """Initialize the event handler with a callback.

        Args:
            event_callback: Function called with file path when JSONL modified
        """
        super().__init__()
        self.event_callback = event_callback
        self.debounce_timers: dict[str, threading.Timer] = {}
        self.debounce_lock = threading.Lock()

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events.

        Filters for .jsonl files only, ignores temporary files, and debounces
        rapid successive events for the same file.

        Args:
            event: File system event from watchdog
        """
        # Ignore directory modifications
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Filter for .jsonl files only
        if file_path.suffix != ".jsonl":
            return

        # Ignore temporary files (starting with . or ending with ~)
        if file_path.name.startswith(".") or file_path.name.endswith("~"):
            return

        # Debounce: reset timer if file modified again within 100ms
        self._debounce_and_trigger(file_path)

    def _debounce_and_trigger(self, file_path: Path) -> None:
        """Debounce events and trigger callback after 100ms of inactivity.

        Args:
            file_path: Path to the modified file
        """
        path_str = str(file_path)

        with self.debounce_lock:
            # Cancel existing timer for this file if present
            if path_str in self.debounce_timers:
                self.debounce_timers[path_str].cancel()

            # Create new timer that fires after 100ms
            timer = threading.Timer(0.1, self._trigger_callback, args=(file_path,))
            self.debounce_timers[path_str] = timer
            timer.start()

    def _trigger_callback(self, file_path: Path) -> None:
        """Trigger the callback and clean up timer.

        Args:
            file_path: Path to the modified file
        """
        path_str = str(file_path)

        # Remove timer from tracking
        with self.debounce_lock:
            if path_str in self.debounce_timers:
                del self.debounce_timers[path_str]

        # Call the registered callback
        self.event_callback(file_path)


class SessionsWatcher:
    """Monitors directories for .jsonl file changes and triggers callbacks.

    Uses watchdog's Observer to watch multiple directories recursively,
    filtering for JSONL file modifications and debouncing rapid events.

    Attributes:
        watch_paths: List of directory paths to monitor
        event_callback: Callback function invoked on file modifications
        _observer: Watchdog Observer instance for file system monitoring
        _handler: Custom event handler with filtering and debouncing
    """

    def __init__(
        self, watch_paths: list[Path], event_callback: Callable[[Path], None]
    ) -> None:
        """Initialize the watcher with paths and callback.

        Args:
            watch_paths: List of directory paths to watch recursively
            event_callback: Function called when a JSONL file is modified
        """
        self.watch_paths = watch_paths
        self.event_callback = event_callback
        self._observer: Observer | None = None
        self._handler = _DebouncedEventHandler(event_callback)

    def start(self) -> None:
        """Start file system monitoring.

        Initializes the Observer and schedules handlers for each watch path
        with recursive=True to monitor subdirectories.
        """
        self._observer = Observer()

        # Schedule a handler for each watch path
        for path in self.watch_paths:
            if path.exists() and path.is_dir():
                self._observer.schedule(self._handler, str(path), recursive=True)

        # Start the observer thread
        self._observer.start()

    def stop(self) -> None:
        """Stop file system monitoring gracefully.

        Stops the Observer and waits for the monitoring thread to complete.
        """
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
