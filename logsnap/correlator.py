"""Event correlation: group related log events by a shared key within a time window."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from logsnap.aggregator import LogEvent


@dataclass
class CorrelationGroup:
    key: str
    events: List[LogEvent] = field(default_factory=list)
    opened_at: float = field(default_factory=time.monotonic)

    def add(self, event: LogEvent) -> None:
        self.events.append(event)

    def age(self, now: Optional[float] = None) -> float:
        return (now or time.monotonic()) - self.opened_at

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "count": len(self.events),
            "opened_at": self.opened_at,
            "sources": list({e.source for e in self.events}),
        }


class EventCorrelator:
    """Groups LogEvents that share a correlation key extracted via regex.

    When a group exceeds *max_size* events or *window_seconds* elapses since
    the first event, the group is flushed to *on_flush*.
    """

    def __init__(
        self,
        pattern: str,
        on_flush: Callable[[CorrelationGroup], None],
        window_seconds: float = 5.0,
        max_size: int = 100,
        _mono: Callable[[], float] = time.monotonic,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        self._re = re.compile(pattern)
        self._on_flush = on_flush
        self._window = window_seconds
        self._max_size = max_size
        self._mono = _mono
        self._groups: Dict[str, CorrelationGroup] = {}

    def record(self, event: LogEvent) -> None:
        """Feed an event into the correlator."""
        self._expire_old()
        m = self._re.search(event.line)
        if not m:
            return
        key = m.group(1) if m.lastindex else m.group(0)
        group = self._groups.setdefault(key, CorrelationGroup(key=key, opened_at=self._mono()))
        group.add(event)
        if len(group.events) >= self._max_size:
            self._flush(key)

    def flush_all(self) -> None:
        """Flush every open group immediately."""
        for key in list(self._groups):
            self._flush(key)

    def _expire_old(self) -> None:
        now = self._mono()
        for key in list(self._groups):
            if self._groups[key].age(now) >= self._window:
                self._flush(key)

    def _flush(self, key: str) -> None:
        group = self._groups.pop(key, None)
        if group and group.events:
            self._on_flush(group)

    def __repr__(self) -> str:  # pragma: no cover
        return f"EventCorrelator(pattern={self._re.pattern!r}, window={self._window}s, groups={len(self._groups)})"
