"""Line sampling — keep only 1-in-N matching events to reduce volume."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SamplerStats:
    seen: int = 0
    emitted: int = 0
    dropped: int = 0

    def to_dict(self) -> dict:
        return {
            "seen": self.seen,
            "emitted": self.emitted,
            "dropped": self.dropped,
        }


class LineSampler:
    """Deterministic 1-in-N sampler per source tag.

    If *rate* is 1 every event is forwarded (no-op).  If *rate* is N,
    the sampler forwards the first event and then skips the next N-1,
    cycling indefinitely.
    """

    def __init__(self, rate: int = 1) -> None:
        if rate < 1:
            raise ValueError(f"rate must be >= 1, got {rate}")
        self._rate = rate
        self._lock = threading.Lock()
        # per-source counter: how many events seen since last emit
        self._counters: dict[str, int] = {}
        self._stats: dict[str, SamplerStats] = {}

    # ------------------------------------------------------------------
    @property
    def rate(self) -> int:
        return self._rate

    def _stats_for(self, source: str) -> SamplerStats:
        if source not in self._stats:
            self._stats[source] = SamplerStats()
        return self._stats[source]

    def should_emit(self, source: str) -> bool:
        """Return True if this event should be forwarded."""
        if self._rate == 1:
            with self._lock:
                s = self._stats_for(source)
                s.seen += 1
                s.emitted += 1
            return True

        with self._lock:
            s = self._stats_for(source)
            s.seen += 1
            count = self._counters.get(source, 0)
            if count == 0:
                self._counters[source] = 1
                s.emitted += 1
                return True
            else:
                next_count = count + 1
                if next_count >= self._rate:
                    next_count = 0
                self._counters[source] = next_count
                s.dropped += 1
                return False

    def stats(self, source: Optional[str] = None) -> dict:
        """Return stats dict for one source or all sources."""
        with self._lock:
            if source is not None:
                return self._stats_for(source).to_dict()
            return {src: st.to_dict() for src, st in self._stats.items()}

    def reset(self, source: Optional[str] = None) -> None:
        """Reset counters (all sources or a specific one)."""
        with self._lock:
            if source is not None:
                self._counters.pop(source, None)
                self._stats.pop(source, None)
            else:
                self._counters.clear()
                self._stats.clear()

    def __repr__(self) -> str:  # pragma: no cover
        return f"LineSampler(rate={self._rate})"
