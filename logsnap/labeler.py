"""Static label injection — attaches fixed key/value metadata to every event."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from logsnap.aggregator import LogEvent


@dataclass
class LabelRule:
    """A single static label to attach to matching events."""

    key: str
    value: Any
    sources: List[str] = field(default_factory=list)  # empty → all sources

    def matches(self, event: LogEvent) -> bool:
        """Return True if this rule applies to *event*."""
        if not self.sources:
            return True
        return event.source in self.sources

    def apply(self, event: LogEvent) -> LogEvent:
        """Return a new event with the label injected into its tags."""
        if not self.matches(event):
            return event
        updated = dict(event.tags)
        updated[self.key] = self.value
        return LogEvent(source=event.source, line=event.line, tags=updated)

    def __repr__(self) -> str:
        src = f", sources={self.sources!r}" if self.sources else ""
        return f"LabelRule(key={self.key!r}, value={self.value!r}{src})"


class Labeler:
    """Applies an ordered list of :class:`LabelRule` objects to events."""

    def __init__(self, rules: List[LabelRule] | None = None) -> None:
        self._rules: List[LabelRule] = list(rules or [])

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_rule(self, rule: LabelRule) -> None:
        self._rules.append(rule)

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def apply(self, event: LogEvent) -> LogEvent:
        """Run all rules in order and return the (possibly modified) event."""
        for rule in self._rules:
            event = rule.apply(event)
        return event

    @property
    def rules(self) -> List[LabelRule]:
        return list(self._rules)

    def __repr__(self) -> str:
        return f"Labeler(rules={self._rules!r})"
