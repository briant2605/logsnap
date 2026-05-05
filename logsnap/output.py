"""Output formatters for LogEvent streams."""

from __future__ import annotations

import json
import sys
from typing import IO, Iterable

from logsnap.aggregator import LogEvent


class PlainFormatter:
    """Writes events as ``[source] line`` to a stream."""

    def __init__(self, stream: IO[str] = sys.stdout, colorize: bool = False) -> None:
        self._stream = stream
        self._colorize = colorize

    # ANSI colour codes keyed by a simple hash of the source name
    _COLORS = ["\033[36m", "\033[32m", "\033[33m", "\033[35m", "\033[34m"]
    _RESET = "\033[0m"

    def _color_for(self, source: str) -> str:
        return self._COLORS[hash(source) % len(self._COLORS)]

    def format(self, event: LogEvent) -> str:
        if self._colorize:
            color = self._color_for(event.source)
            return f"{color}[{event.source}]{self._RESET} {event.line}"
        return f"[{event.source}] {event.line}"

    def emit(self, events: Iterable[LogEvent]) -> None:
        for event in events:
            self._stream.write(self.format(event) + "\n")
            self._stream.flush()


class JsonFormatter:
    """Writes events as newline-delimited JSON objects."""

    def __init__(self, stream: IO[str] = sys.stdout) -> None:
        self._stream = stream

    def format(self, event: LogEvent) -> str:
        return json.dumps({"source": event.source, "line": event.line})

    def emit(self, events: Iterable[LogEvent]) -> None:
        for event in events:
            self._stream.write(self.format(event) + "\n")
            self._stream.flush()
