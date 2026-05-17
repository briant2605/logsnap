"""Event aggregation: bucket events by key and emit summaries periodically."""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class AggregationBucket:
    key: str
    count: int = 0
    first_seen: float = field(default_factory=time.monotonic)
    last_seen: float = field(default_factory=time.monotonic)
    samples: List[str] = field(default_factory=list)
    max_samples: int = 3

    def add(self, line: str) -> None:
        self.count += 1
        self.last_seen = time.monotonic()
        if len(self.samples) < self.max_samples:
            self.samples.append(line)

    def age(self) -> float:
        return time.monotonic() - self.first_seen

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "samples": list(self.samples),
        }


class EventAggregator:
    """Groups events by a key function and flushes summaries on a schedule."""

    def __init__(
        self,
        key_fn: Callable[[str, str], str],
        flush_interval: float = 60.0,
        on_flush: Optional[Callable[[List[AggregationBucket]], None]] = None,
        max_samples: int = 3,
    ) -> None:
        if flush_interval <= 0:
            raise ValueError("flush_interval must be positive")
        self._key_fn = key_fn
        self._flush_interval = flush_interval
        self._on_flush = on_flush
        self._max_samples = max_samples
        self._buckets: Dict[str, AggregationBucket] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def record(self, source: str, line: str) -> None:
        key = self._key_fn(source, line)
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = AggregationBucket(key=key, max_samples=self._max_samples)
            self._buckets[key].add(line)

    def flush(self) -> List[AggregationBucket]:
        with self._lock:
            buckets = list(self._buckets.values())
            self._buckets.clear()
        if self._on_flush and buckets:
            self._on_flush(buckets)
        return buckets

    def bucket_count(self) -> int:
        with self._lock:
            return len(self._buckets)

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="aggregator-flush")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: float = 5.0) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        while not self._stop.wait(self._flush_interval):
            self.flush()
        self.flush()
