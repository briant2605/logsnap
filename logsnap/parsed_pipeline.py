"""Pipeline variant that parses each log line into structured fields.

Wraps an inner Pipeline/SampledPipeline and attaches parsed fields to
each LogEvent before forwarding it downstream.
"""
from __future__ import annotations

import threading
from queue import Queue
from typing import Any, Optional

from logsnap.aggregator import LogEvent
from logsnap.parser import LineParser


class ParsedPipeline:
    """Decorates an inner pipeline by parsing event lines before forwarding."""

    def __init__(
        self,
        inner: Any,
        parser: LineParser,
        *,
        queue_size: int = 1000,
    ) -> None:
        if not hasattr(inner, "start") or not hasattr(inner, "stop"):
            raise TypeError("inner must expose start() and stop()")
        self._inner = inner
        self._parser = parser
        self._queue: Queue[Optional[LogEvent]] = Queue(maxsize=queue_size)
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ------------------------------------------------------------------
    # Public interface mirrors Pipeline / SampledPipeline
    # ------------------------------------------------------------------

    def put(self, event: LogEvent) -> None:
        """Enqueue an event for parsing and forwarding."""
        self._queue.put(event)

    def start(self) -> None:
        self._running = True
        self._inner.start()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._queue.put(None)  # sentinel
        self._inner.stop()

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        if hasattr(self._inner, "join"):
            self._inner.join(timeout=timeout)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        while self._running:
            event = self._queue.get()
            if event is None:
                break
            self._process(event)

    def _process(self, event: LogEvent) -> None:
        fields = self._parser.parse(event.line)
        # Attach parsed fields as extra metadata without mutating the original
        enriched = LogEvent(
            source=event.source,
            line=event.line,
            timestamp=event.timestamp,
        )
        enriched.fields = fields  # type: ignore[attr-defined]
        self._inner.put(enriched)
