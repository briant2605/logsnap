"""Event classifier: assigns a named category to log events based on pattern rules."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from logsnap.aggregator import LogEvent


@dataclass
class ClassifyRule:
    """Assign *category* to events whose line matches *pattern*."""

    pattern: str
    category: str
    source: Optional[str] = None  # restrict to a specific source tag
    _regex: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._regex = re.compile(self.pattern)

    def matches(self, event: LogEvent) -> bool:
        if self.source and event.source != self.source:
            return False
        return bool(self._regex.search(event.line))

    def apply(self, event: LogEvent) -> LogEvent:
        """Return a copy of *event* with the category tag injected."""
        tags = dict(event.tags) if event.tags else {}
        tags["category"] = self.category
        return LogEvent(source=event.source, line=event.line, tags=tags)

    def __repr__(self) -> str:  # pragma: no cover
        return f"ClassifyRule(pattern={self.pattern!r}, category={self.category!r})"


class EventClassifier:
    """Apply an ordered list of :class:`ClassifyRule` objects to events.

    The first matching rule wins.  If no rule matches the event is returned
    unchanged (category tag is **not** set).
    """

    def __init__(self, default_category: Optional[str] = None) -> None:
        self._rules: List[ClassifyRule] = []
        self._default_category = default_category
        self._callbacks: List[Callable[[LogEvent, str], None]] = []

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def add_rule(self, rule: ClassifyRule) -> None:
        self._rules.append(rule)

    def on_classify(self, callback: Callable[[LogEvent, str], None]) -> None:
        """Register a callback invoked with *(event, category)* on each match."""
        self._callbacks.append(callback)

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------

    def classify(self, event: LogEvent) -> LogEvent:
        """Return the event annotated with a *category* tag."""
        for rule in self._rules:
            if rule.matches(event):
                result = rule.apply(event)
                for cb in self._callbacks:
                    cb(result, rule.category)
                return result

        if self._default_category is not None:
            tags = dict(event.tags) if event.tags else {}
            tags["category"] = self._default_category
            return LogEvent(source=event.source, line=event.line, tags=tags)

        return event

    def categories(self) -> Dict[str, int]:
        """Return a mapping of category name -> number of rules for that category."""
        counts: Dict[str, int] = {}
        for rule in self._rules:
            counts[rule.category] = counts.get(rule.category, 0) + 1
        return counts

    def __repr__(self) -> str:  # pragma: no cover
        return f"EventClassifier(rules={len(self._rules)}, default={self._default_category!r})"
