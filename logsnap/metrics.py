"""Lightweight in-process metrics collector for logsnap."""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class SourceMetrics:
    lines_read: int = 0
    lines_matched: int = 0
    bytes_read: int = 0
    rotations: int = 0
    last_event_ts: float = 0.0

    def to_dict(self) -> dict:
        return {
            "lines_read": self.lines_read,
            "lines_matched": self.lines_matched,
            "bytes_read": self.bytes_read,
            "rotations": self.rotations,
            "last_event_ts": self.last_event_ts,
        }


class MetricsCollector:
    """Thread-safe collector that tracks per-source and global counters."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sources: Dict[str, SourceMetrics] = defaultdict(SourceMetrics)
        self._start_time: float = time.monotonic()

    def record_line(self, source: str, line: str, matched: bool) -> None:
        """Record a line read from *source*."""
        with self._lock:
            m = self._sources[source]
            m.lines_read += 1
            m.bytes_read += len(line.encode())
            m.last_event_ts = time.time()
            if matched:
                m.lines_matched += 1

    def record_rotation(self, source: str) -> None:
        """Increment the rotation counter for *source*."""
        with self._lock:
            self._sources[source].rotations += 1

    def snapshot(self) -> dict:
        """Return a point-in-time snapshot of all metrics."""
        with self._lock:
            return {
                "uptime_seconds": round(time.monotonic() - self._start_time, 2),
                "sources": {
                    src: m.to_dict() for src, m in self._sources.items()
                },
            }

    def reset(self) -> None:
        """Clear all counters (useful in tests)."""
        with self._lock:
            self._sources.clear()
            self._start_time = time.monotonic()
