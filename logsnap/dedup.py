"""Deduplication filter: suppress repeated identical log lines within a time window."""

import time
from collections import OrderedDict
from typing import Optional


class DedupFilter:
    """Suppress duplicate log lines seen within *window* seconds.

    Uses an LRU-style OrderedDict so memory stays bounded to *max_entries*.
    """

    def __init__(
        self,
        window: float = 5.0,
        max_entries: int = 1024,
        _mono=None,
    ) -> None:
        if window < 0:
            raise ValueError("window must be >= 0")
        self._window = window
        self._max = max_entries
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._mono = _mono or time.monotonic

    # ------------------------------------------------------------------
    def is_duplicate(self, line: str) -> bool:
        """Return True if *line* was already seen within the dedup window."""
        now = self._mono()
        if line in self._seen:
            last = self._seen[line]
            if now - last < self._window:
                # Move to end (most-recently used)
                self._seen.move_to_end(line)
                return True
            # Expired — treat as new
        self._seen[line] = now
        self._seen.move_to_end(line)
        # Evict oldest entries when over capacity
        while len(self._seen) > self._max:
            self._seen.popitem(last=False)
        return False

    def reset(self) -> None:
        """Clear all tracked entries."""
        self._seen.clear()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"DedupFilter(window={self._window}, "
            f"max_entries={self._max}, tracked={len(self._seen)})"
        )
