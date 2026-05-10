"""Pipeline wrapper that applies per-source rate limiting via ThrottleManager."""

from __future__ import annotations

import queue
import threading
from typing import Callable, Optional

from logsnap.aggregator import LogEvent
from logsnap.throttle import ThrottleManager
from logsnap.metrics import MetricsCollector


class RateLimitedPipeline:
    """Wraps an inner event handler and drops events that exceed the rate limit."""

    def __init__(
        self,
        handler: Callable[[LogEvent], None],
        throttle: ThrottleManager,
        metrics: Optional[MetricsCollector] = None,
        maxsize: int = 1000,
    ) -> None:
        self._handler = handler
        self._throttle = throttle
        self._metrics = metrics
        self._queue: queue.Queue[Optional[LogEvent]] = queue.Queue(maxsize=maxsize)
        self._thread: Optional[threading.Thread] = None
        self._dropped: int = 0

    @property
    def dropped(self) -> int:
        return self._dropped

    def put(self, event: LogEvent) -> None:
        """Enqueue an event for processing; drops silently if queue is full."""
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            self._dropped += 1

    def _run_loop(self) -> None:
        while True:
            event = self._queue.get()
            if event is None:
                break
            source = event.source
            if self._throttle.allow(source):
                self._handler(event)
                if self._metrics:
                    self._metrics.record_line(source, matched=True)
            else:
                self._dropped += 1
                if self._metrics:
                    self._metrics.record_line(source, matched=False)

    def start(self) -> "RateLimitedPipeline":
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ratelimit-pipeline")
        self._thread.start()
        return self

    def stop(self) -> None:
        self._queue.put(None)

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)
