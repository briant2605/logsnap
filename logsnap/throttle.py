"""Rate limiting / throttle support for log line emission.

Allows capping the number of lines emitted per source per second to
avoid overwhelming downstream consumers when a log file is flooded.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class _Bucket:
    """Token-bucket state for a single source."""
    tokens: float
    last_refill: float = field(default_factory=time.monotonic)


class ThrottleManager:
    """Per-source token-bucket rate limiter.

    Parameters
    ----------
    rate:
        Maximum lines allowed per second for each source.
        ``None`` or ``0`` disables throttling entirely.
    burst:
        Maximum burst size (bucket capacity).  Defaults to *rate* when
        not supplied, meaning no burst above the steady-state rate.
    """

    def __init__(self, rate: Optional[float] = None, burst: Optional[float] = None) -> None:
        self.rate: Optional[float] = float(rate) if rate else None
        self.burst: float = float(burst) if burst else (self.rate or 0.0)
        self._buckets: Dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(tokens=self.burst)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self, source: str) -> bool:
        """Return ``True`` if a line from *source* should be forwarded.

        Consumes one token from the bucket.  If the bucket is empty the
        line is dropped and ``False`` is returned.
        """
        if not self.rate:
            return True

        bucket = self._buckets[source]
        self._refill(bucket)

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True
        return False

    def reset(self, source: str) -> None:
        """Reset the bucket for *source* to full capacity."""
        if source in self._buckets:
            del self._buckets[source]

    def stats(self, source: str) -> Dict[str, float]:
        """Return current bucket state for *source* (useful for metrics)."""
        if source not in self._buckets:
            return {"tokens": self.burst, "rate": self.rate or 0.0}
        bucket = self._buckets[source]
        self._refill(bucket)
        return {"tokens": bucket.tokens, "rate": self.rate or 0.0}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refill(self, bucket: _Bucket) -> None:
        now = time.monotonic()
        elapsed = now - bucket.last_refill
        bucket.tokens = min(self.burst, bucket.tokens + elapsed * (self.rate or 0.0))
        bucket.last_refill = now

    def __repr__(self) -> str:  # pragma: no cover
        return f"ThrottleManager(rate={self.rate}, burst={self.burst})"
