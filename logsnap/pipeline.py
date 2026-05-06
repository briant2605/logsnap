"""Event processing pipeline: filter → dedup → throttle → emit."""

import queue
import threading
from typing import Optional

from logsnap.aggregator import LogEvent
from logsnap.filter import LineFilter
from logsnap.output import PlainFormatter
from logsnap.metrics import MetricsCollector
from logsnap.throttle import ThrottleManager
from logsnap.dedup import DedupFilter


class Pipeline:
    """Consume *LogEvent* objects from a queue, apply filter/dedup/throttle,
    then emit via a formatter.
    """

    def __init__(
        self,
        event_queue: queue.Queue,
        line_filter: Optional[LineFilter] = None,
        formatter=None,
        metrics: Optional[MetricsCollector] = None,
        throttle: Optional[ThrottleManager] = None,
        dedup: Optional[DedupFilter] = None,
        stream=None,
    ) -> None:
        self._q = event_queue
        self._filter = line_filter or LineFilter()
        self._formatter = formatter or PlainFormatter(stream=stream)
        self._metrics = metrics
        self._throttle = throttle
        self._dedup = dedup
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    def _process_event(self, event: LogEvent) -> None:
        matched = self._filter.matches(event.line)
        if self._metrics:
            self._metrics.record_line(event.source, matched=matched)
        if not matched:
            return
        if self._dedup and self._dedup.is_duplicate(event.line):
            return
        if self._throttle and not self._throttle.allow(event.source):
            return
        self._formatter.emit(event)

    def _run_loop(self) -> None:
        while not self._stop.is_set():
            try:
                event = self._q.get(timeout=0.1)
            except queue.Empty:
                continue
            self._process_event(event)
            self._q.task_done()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def drain(self) -> None:
        """Process all currently queued events synchronously (useful in tests)."""
        while not self._q.empty():
            try:
                event = self._q.get_nowait()
            except queue.Empty:
                break
            self._process_event(event)
            self._q.task_done()
