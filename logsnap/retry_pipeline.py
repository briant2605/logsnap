"""Pipeline stage that wraps output emission with retry logic."""
from __future__ import annotations

import queue
import threading
from typing import Callable, Iterable, Optional

from logsnap.aggregator import LogEvent
from logsnap.retry import RetryEmitter, RetryPolicy


class RetryPipeline:
    """Consume LogEvents from an input queue and emit with retry.

    Integrates RetryEmitter so that transient write errors are retried
    according to the configured RetryPolicy before a line is dropped.
    """

    def __init__(
        self,
        emit: Callable[[str], None],
        policy: Optional[RetryPolicy] = None,
        maxsize: int = 1000,
    ) -> None:
        self._queue: queue.Queue[Optional[LogEvent]] = queue.Queue(maxsize=maxsize)
        self._emitter = RetryEmitter(
            emit=emit,
            policy=policy or RetryPolicy(),
            sleep_fn=__import__("time").sleep,
        )
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def stats(self):
        return self._emitter.stats

    def put(self, event: LogEvent) -> None:
        self._queue.put(event)

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="retry-pipeline"
        )
        self._thread.start()

    def stop(self) -> None:
        self._queue.put(None)  # sentinel
        self._stop_event.set()

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        while True:
            try:
                event = self._queue.get(timeout=0.1)
            except queue.Empty:
                if self._stop_event.is_set():
                    break
                continue
            if event is None:
                break
            self._emitter.emit(str(event))
