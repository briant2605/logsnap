"""Multiline log event assembler.

Groups consecutive log lines into a single logical event when continuation
lines match a configurable pattern (e.g. stack traces indented with spaces).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class MultilineConfig:
    """Configuration for multiline grouping."""
    # Regex that identifies the *start* of a new event.
    start_pattern: str = r"^\S"
    # Maximum number of lines in a single assembled event.
    max_lines: int = 500
    # Seconds to wait before flushing an incomplete group.
    flush_timeout: float = 2.0

    def __post_init__(self) -> None:
        self._re = re.compile(self.start_pattern)

    def is_start(self, line: str) -> bool:
        return bool(self._re.search(line))


class MultilineAssembler:
    """Accumulates lines and emits assembled events via a callback."""

    def __init__(
        self,
        config: MultilineConfig,
        emit: Callable[[str], None],
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cfg = config
        self._emit = emit
        self._clock = clock
        self._buf: List[str] = []
        self._last_ts: float = 0.0

    # ------------------------------------------------------------------
    def feed(self, line: str) -> None:
        """Feed one raw line into the assembler."""
        if self._cfg.is_start(line) or len(self._buf) >= self._cfg.max_lines:
            self._flush()
        self._buf.append(line)
        self._last_ts = self._clock()

    def flush_if_stale(self) -> None:
        """Flush pending buffer if the flush timeout has elapsed."""
        if self._buf and (self._clock() - self._last_ts) >= self._cfg.flush_timeout:
            self._flush()

    def flush(self) -> None:
        """Unconditionally flush any pending buffer."""
        self._flush()

    # ------------------------------------------------------------------
    def _flush(self) -> None:
        if self._buf:
            self._emit("\n".join(self._buf))
            self._buf = []
