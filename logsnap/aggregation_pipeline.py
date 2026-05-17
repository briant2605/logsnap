"""Pipeline stage that records events into an EventAggregator."""
from __future__ import annotations

import queue
import threading
from typing import Callable, List, Optional

from logsnap.aggregation import AggregationBucket, EventAggregator


class AggregationPipeline:
    """Wraps an EventAggregator as a pipeline sink.

    Events placed via ``put`` are recorded into the aggregator.  The
    aggregator's periodic flush runs in its own daemon thread; flushed
    buckets are forwarded to an optional *on_flush* callback.
    """

    def __init__(
        self,
        aggregator: EventAggregator,
        on_flush: Optional[Callable[[List[AggregationBucket]], None]] = None,
        maxsize: int = 1000,
    ) -> None:
        self._aggregator = aggregator
        if on_flush is not None:
            # Wire the callback if not already set.
            if self._aggregator._on_flush is None:
                self._aggregator._on_flush = on_flush
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def put(self, source: str, line: str, block: bool = True, timeout: float = 0.1) -> bool:
        try:
            self._queue.put((source, line), block=block, timeout=timeout)
            return True
        except queue.Full:
            return False

    def flush(self) -> List[AggregationBucket]:
        return self._aggregator.flush()

    def bucket_count(self) -> int:
        return self._aggregator.bucket_count()

    def start(self) -> None:
        self._stop.clear()
        self._aggregator.start()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="agg-pipeline"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._aggregator.stop()

    def join(self, timeout: float = 5.0) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)
        self._aggregator.join(timeout=timeout)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        while not self._stop.is_set():
            try:
                source, line = self._queue.get(timeout=0.1)
                self._aggregator.record(source, line)
            except queue.Empty:
                continue
        # Drain remaining items.
        while True:
            try:
                source, line = self._queue.get_nowait()
                self._aggregator.record(source, line)
            except queue.Empty:
                break
