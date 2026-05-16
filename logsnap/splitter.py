"""Event splitter: fan-out a single LogEvent to multiple output queues."""
from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from logsnap.aggregator import LogEvent


@dataclass
class SplitterStats:
    forwarded: int = 0
    dropped: int = 0

    def to_dict(self) -> dict:
        return {"forwarded": self.forwarded, "dropped": self.dropped}


class EventSplitter:
    """Fan-out incoming LogEvents to one or more registered output queues.

    Each registered sink receives every event.  If a sink queue is full the
    event is counted as dropped for that sink (non-blocking put).
    """

    def __init__(self, maxsize: int = 0) -> None:
        if maxsize < 0:
            raise ValueError("maxsize must be >= 0")
        self._in: queue.Queue[Optional[LogEvent]] = queue.Queue(maxsize=maxsize)
        self._sinks: List[queue.Queue[Optional[LogEvent]]] = []
        self._stats = SplitterStats()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ------------------------------------------------------------------
    def add_sink(self, q: queue.Queue) -> None:  # type: ignore[type-arg]
        """Register an output queue as a fan-out destination."""
        with self._lock:
            self._sinks.append(q)

    @property
    def stats(self) -> SplitterStats:
        return self._stats

    def put(self, event: LogEvent) -> None:
        self._in.put(event)

    # ------------------------------------------------------------------
    def _dispatch(self, event: LogEvent) -> None:
        with self._lock:
            sinks = list(self._sinks)
        for sink in sinks:
            try:
                sink.put_nowait(event)
                self._stats.forwarded += 1
            except queue.Full:
                self._stats.dropped += 1

    def _run_loop(self) -> None:
        while self._running:
            try:
                event = self._in.get(timeout=0.1)
            except queue.Empty:
                continue
            if event is None:
                break
            self._dispatch(event)

    # ------------------------------------------------------------------
    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._in.put(None)

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)
