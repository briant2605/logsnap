"""A pipeline variant that routes processed events through an EventRouter."""
from __future__ import annotations

import queue
import threading
from typing import Optional

from logsnap.aggregator import LogAggregator, LogEvent
from logsnap.filter import LineFilter
from logsnap.metrics import MetricsCollector
from logsnap.routing import EventRouter


class RoutedPipeline:
    """Reads events from a LogAggregator, applies a filter, then routes each
    matching event via an EventRouter to registered channel handlers.
    """

    def __init__(
        self,
        aggregator: LogAggregator,
        router: EventRouter,
        line_filter: Optional[LineFilter] = None,
        metrics: Optional[MetricsCollector] = None,
        poll_interval: float = 0.05,
    ) -> None:
        self._aggregator = aggregator
        self._router = router
        self._filter = line_filter or LineFilter()
        self._metrics = metrics or MetricsCollector()
        self._poll_interval = poll_interval
        self._queue: queue.Queue[Optional[LogEvent]] = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._aggregator.start(self._queue)
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._aggregator.stop()

    def join(self, timeout: float = 2.0) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                event: Optional[LogEvent] = self._queue.get(
                    timeout=self._poll_interval
                )
            except queue.Empty:
                continue
            if event is None:
                break
            self._process(event)

    def _process(self, event: LogEvent) -> None:
        if self._filter.matches(event.line):
            self._metrics.record_line(event.source, matched=True)
            self._router.route(event)
        else:
            self._metrics.record_line(event.source, matched=False)

    def __repr__(self) -> str:
        return (
            f"RoutedPipeline(router={self._router!r}, "
            f"filter={self._filter!r})"
        )
