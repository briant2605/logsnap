"""Pipeline: wires together tailer, filter, throttle, metrics, and output."""
from __future__ import annotations

import threading
from typing import List, Optional

from logsnap.aggregator import LogAggregator, LogEvent
from logsnap.filter import LineFilter
from logsnap.metrics import MetricsCollector
from logsnap.output import PlainFormatter, JsonFormatter, BaseFormatter
from logsnap.throttle import ThrottleManager


class Pipeline:
    """Connects aggregation, filtering, throttling, metrics, and output."""

    def __init__(
        self,
        aggregator: LogAggregator,
        line_filter: Optional[LineFilter] = None,
        throttle: Optional[ThrottleManager] = None,
        metrics: Optional[MetricsCollector] = None,
        formatter: Optional[BaseFormatter] = None,
        output_stream=None,
    ) -> None:
        self._aggregator = aggregator
        self._filter = line_filter or LineFilter()
        self._throttle = throttle or ThrottleManager({})
        self._metrics = metrics or MetricsCollector()
        self._formatter = formatter or PlainFormatter(use_color=False)
        self._stream = output_stream
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    def _process_event(self, event: LogEvent) -> None:
        source = event.source
        line = event.line

        if not self._filter.matches(line):
            self._metrics.record_line(source, matched=False)
            return

        if not self._throttle.allow(source):
            self._metrics.record_line(source, matched=True)
            return

        self._metrics.record_line(source, matched=True)
        self._formatter.emit(event, stream=self._stream)

    # ------------------------------------------------------------------
    def _run_loop(self) -> None:
        for event in self._aggregator.events(stop_event=self._stop_event):
            self._process_event(event)

    def start(self) -> None:
        """Start the pipeline in a background thread."""
        self._aggregator.start()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the pipeline to stop and wait for clean shutdown."""
        self._stop_event.set()
        self._aggregator.stop()
        if self._thread:
            self._thread.join(timeout=timeout)

    @property
    def metrics(self) -> MetricsCollector:
        return self._metrics
