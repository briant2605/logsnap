"""Aggregator: coordinates multiple LogTailers and applies a LineFilter."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional

from logsnap.filter import LineFilter
from logsnap.tailer import LogTailer


@dataclass
class LogEvent:
    """A single log line emitted by the aggregator."""

    source: str
    line: str

    def __str__(self) -> str:  # pragma: no cover
        return f"[{self.source}] {self.line}"


class LogAggregator:
    """Tails multiple files concurrently and emits filtered LogEvent objects."""

    def __init__(
        self,
        paths: Iterable[str | Path],
        line_filter: Optional[LineFilter] = None,
        poll_interval: float = 0.1,
    ) -> None:
        self._paths = [Path(p) for p in paths]
        self._filter = line_filter or LineFilter()
        self._poll_interval = poll_interval
        self._event_queue: queue.Queue[LogEvent] = queue.Queue()
        self._threads: list[threading.Thread] = []
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Spawn a background thread per file path."""
        self._stop_event.clear()
        for path in self._paths:
            t = threading.Thread(
                target=self._tail_worker,
                args=(path,),
                daemon=True,
                name=f"tailer-{path.name}",
            )
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        """Signal all tailer threads to stop."""
        self._stop_event.set()

    def events(self, timeout: float = 0.2) -> Iterable[LogEvent]:
        """Yield LogEvent objects as they arrive; returns when stopped."""
        while not self._stop_event.is_set() or not self._event_queue.empty():
            try:
                yield self._event_queue.get(timeout=timeout)
            except queue.Empty:
                continue

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _tail_worker(self, path: Path) -> None:
        tailer = LogTailer(str(path), poll_interval=self._poll_interval)
        for line in tailer.tail(stop_event=self._stop_event):
            if self._filter.matches(line):
                self._event_queue.put(LogEvent(source=path.name, line=line))
