"""Bounded in-memory ring buffer for log events with overflow tracking."""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, List, Optional

from logsnap.aggregator import LogEvent


@dataclass
class BufferStats:
    total_enqueued: int = 0
    total_dropped: int = 0
    current_size: int = 0

    def to_dict(self) -> dict:
        return {
            "total_enqueued": self.total_enqueued,
            "total_dropped": self.total_dropped,
            "current_size": self.current_size,
        }


class EventBuffer:
    """Thread-safe ring buffer that drops the oldest event when full."""

    def __init__(
        self,
        maxsize: int = 1000,
        on_drop: Optional[Callable[[LogEvent], None]] = None,
    ) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self._maxsize = maxsize
        self._queue: Deque[LogEvent] = deque()
        self._lock = threading.Lock()
        self._stats = BufferStats()
        self._on_drop = on_drop

    # ------------------------------------------------------------------
    def put(self, event: LogEvent) -> bool:
        """Add *event* to the buffer.  Returns True if accepted, False if dropped."""
        dropped_event: Optional[LogEvent] = None
        with self._lock:
            if len(self._queue) >= self._maxsize:
                dropped_event = self._queue.popleft()
                self._stats.total_dropped += 1
            self._queue.append(event)
            self._stats.total_enqueued += 1
            self._stats.current_size = len(self._queue)
        if dropped_event is not None and self._on_drop:
            self._on_drop(dropped_event)
        return dropped_event is None

    def drain(self, max_items: Optional[int] = None) -> List[LogEvent]:
        """Remove and return up to *max_items* events (all if None)."""
        with self._lock:
            if max_items is None:
                items = list(self._queue)
                self._queue.clear()
            else:
                items = [self._queue.popleft() for _ in range(min(max_items, len(self._queue)))]
            self._stats.current_size = len(self._queue)
        return items

    def peek(self) -> List[LogEvent]:
        """Return a snapshot of current events without removing them."""
        with self._lock:
            return list(self._queue)

    @property
    def stats(self) -> BufferStats:
        with self._lock:
            return BufferStats(
                total_enqueued=self._stats.total_enqueued,
                total_dropped=self._stats.total_dropped,
                current_size=self._stats.current_size,
            )

    def __len__(self) -> int:
        with self._lock:
            return len(self._queue)
