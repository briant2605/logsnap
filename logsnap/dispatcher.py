"""Event dispatcher: fan-out a single event to multiple named sinks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from logsnap.aggregator import LogEvent


@dataclass
class DispatchStats:
    dispatched: int = 0
    dropped: int = 0
    sink_errors: int = 0

    def to_dict(self) -> dict:
        return {
            "dispatched": self.dispatched,
            "dropped": self.dropped,
            "sink_errors": self.sink_errors,
        }


SinkFn = Callable[[LogEvent], None]


class EventDispatcher:
    """Fan-out dispatcher that sends each event to all registered sinks.

    Sinks are identified by name so they can be added, removed, or
    replaced at runtime.  If a sink raises, the error is counted and
    the remaining sinks still receive the event.
    """

    def __init__(self, error_handler: Optional[Callable[[str, Exception], None]] = None) -> None:
        self._sinks: Dict[str, SinkFn] = {}
        self._stats = DispatchStats()
        self._error_handler = error_handler

    # ------------------------------------------------------------------
    # Sink management
    # ------------------------------------------------------------------

    def add_sink(self, name: str, fn: SinkFn) -> None:
        """Register *fn* under *name*, replacing any previous entry."""
        if not callable(fn):
            raise TypeError(f"sink '{name}' must be callable, got {type(fn)}")
        self._sinks[name] = fn

    def remove_sink(self, name: str) -> bool:
        """Remove the sink registered as *name*.  Returns True if it existed."""
        return self._sinks.pop(name, None) is not None

    def sink_names(self) -> List[str]:
        return list(self._sinks)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, event: LogEvent) -> None:
        """Send *event* to every registered sink."""
        if not self._sinks:
            self._stats.dropped += 1
            return

        for name, fn in list(self._sinks.items()):
            try:
                fn(event)
            except Exception as exc:  # noqa: BLE001
                self._stats.sink_errors += 1
                if self._error_handler is not None:
                    self._error_handler(name, exc)

        self._stats.dispatched += 1

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def stats(self) -> DispatchStats:
        return self._stats

    def reset_stats(self) -> None:
        self._stats = DispatchStats()

    def __repr__(self) -> str:  # pragma: no cover
        return f"EventDispatcher(sinks={list(self._sinks)!r})"
