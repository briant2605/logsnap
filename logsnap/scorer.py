"""Event severity scorer: assigns a numeric score to log events based on pattern rules."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from logsnap.aggregator import LogEvent


@dataclass
class ScoreRule:
    pattern: str
    score: float
    source: Optional[str] = None
    _re: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._re = re.compile(self.pattern)

    def matches(self, event: LogEvent) -> bool:
        if self.source and event.source != self.source:
            return False
        return bool(self._re.search(event.line))

    def __repr__(self) -> str:  # pragma: no cover
        src = f", source={self.source!r}" if self.source else ""
        return f"ScoreRule(pattern={self.pattern!r}, score={self.score}{src})"


class EventScorer:
    """Accumulates ScoreRules and computes a total severity score for an event."""

    def __init__(self, default_score: float = 0.0) -> None:
        if default_score < 0:
            raise ValueError("default_score must be >= 0")
        self._default = default_score
        self._rules: List[ScoreRule] = []
        self._callbacks: List[Callable[[LogEvent, float], None]] = []

    def add_rule(self, rule: ScoreRule) -> None:
        self._rules.append(rule)

    def on_score(self, callback: Callable[[LogEvent, float], None]) -> None:
        """Register a callback invoked with (event, score) after scoring."""
        self._callbacks.append(callback)

    def score(self, event: LogEvent) -> float:
        """Return the cumulative score for *event* (default_score if no rules match)."""
        total = self._default
        matched = False
        for rule in self._rules:
            if rule.matches(event):
                total += rule.score
                matched = True
        result = total if matched else self._default
        for cb in self._callbacks:
            cb(event, result)
        return result

    def rules(self) -> List[ScoreRule]:
        return list(self._rules)

    def __repr__(self) -> str:  # pragma: no cover
        return f"EventScorer(rules={len(self._rules)}, default={self._default})"
