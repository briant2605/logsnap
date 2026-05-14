"""File watchdog: detects log file rotation and truncation events."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional


@dataclass
class FileState:
    inode: int
    size: int

    def to_dict(self) -> dict:
        return {"inode": self.inode, "size": self.size}


class WatchdogEvent:
    ROTATED = "rotated"
    TRUNCATED = "truncated"
    UNCHANGED = "unchanged"
    GREW = "grew"


@dataclass
class FileWatchdog:
    """Monitors a single file path for rotation or truncation."""

    path: str
    on_event: Callable[[str, str], None]  # (event_type, path)
    poll_interval: float = 1.0
    _state: Optional[FileState] = field(default=None, init=False, repr=False)
    _running: bool = field(default=False, init=False, repr=False)

    def _stat(self) -> Optional[FileState]:
        try:
            st = os.stat(self.path)
            return FileState(inode=st.st_ino, size=st.st_size)
        except FileNotFoundError:
            return None

    def check(self) -> str:
        """Perform a single check; returns the event type detected."""
        current = self._stat()
        if current is None:
            return WatchdogEvent.UNCHANGED

        if self._state is None:
            self._state = current
            return WatchdogEvent.UNCHANGED

        if current.inode != self._state.inode:
            self._state = current
            self.on_event(WatchdogEvent.ROTATED, self.path)
            return WatchdogEvent.ROTATED

        if current.size < self._state.size:
            self._state = current
            self.on_event(WatchdogEvent.TRUNCATED, self.path)
            return WatchdogEvent.TRUNCATED

        event = WatchdogEvent.GREW if current.size > self._state.size else WatchdogEvent.UNCHANGED
        self._state = current
        return event

    def start(self, iterations: Optional[int] = None) -> None:
        """Poll in a loop.  *iterations* limits cycles (useful for tests)."""
        self._running = True
        count = 0
        while self._running:
            self.check()
            count += 1
            if iterations is not None and count >= iterations:
                break
            time.sleep(self.poll_interval)

    def stop(self) -> None:
        self._running = False

    def __repr__(self) -> str:  # pragma: no cover
        return f"FileWatchdog(path={self.path!r}, interval={self.poll_interval}s)"
