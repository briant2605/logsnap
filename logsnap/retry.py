"""Retry policy for failed output emissions."""
from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryStats:
    attempts: int = 0
    successes: int = 0
    failures: int = 0
    dropped: int = 0

    def to_dict(self) -> dict:
        return {
            "attempts": self.attempts,
            "successes": self.successes,
            "failures": self.failures,
            "dropped": self.dropped,
        }


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 0.5
    backoff_factor: float = 2.0
    max_delay: float = 10.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be >= 0")
        if self.backoff_factor < 1.0:
            raise ValueError("backoff_factor must be >= 1.0")

    def delay_for(self, attempt: int) -> float:
        """Return sleep duration before the given attempt (0-indexed)."""
        if attempt == 0:
            return 0.0
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)


class RetryEmitter:
    """Wraps an emit callable with retry logic."""

    def __init__(
        self,
        emit: Callable[[str], None],
        policy: Optional[RetryPolicy] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._emit = emit
        self._policy = policy or RetryPolicy()
        self._sleep = sleep_fn
        self.stats = RetryStats()

    def emit(self, line: str) -> bool:
        """Attempt to emit *line*, retrying on exception.

        Returns True if emission succeeded, False if all attempts exhausted.
        """
        policy = self._policy
        for attempt in range(policy.max_attempts):
            delay = policy.delay_for(attempt)
            if delay > 0:
                self._sleep(delay)
            self.stats.attempts += 1
            try:
                self._emit(line)
                self.stats.successes += 1
                return True
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "emit attempt %d/%d failed: %s",
                    attempt + 1,
                    policy.max_attempts,
                    exc,
                )
        self.stats.failures += 1
        self.stats.dropped += 1
        logger.error("dropping line after %d failed attempts", policy.max_attempts)
        return False
