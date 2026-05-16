"""Tag injection for log events based on regex pattern matching."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from logsnap.aggregator import LogEvent


@dataclass
class TagRule:
    """Applies a fixed tag to events whose line matches *pattern*."""

    pattern: str
    tag: str
    value: object = True
    source: Optional[str] = None  # restrict to a specific source, or None = all

    def __post_init__(self) -> None:
        self._re = re.compile(self.pattern)

    def matches(self, event: LogEvent) -> bool:
        if self.source is not None and event.source != self.source:
            return False
        return bool(self._re.search(event.line))

    def apply(self, event: LogEvent) -> LogEvent:
        """Return a new LogEvent with the tag injected into its *tags* dict."""
        tags: Dict[str, object] = dict(event.tags) if event.tags else {}
        tags[self.tag] = self.value
        return LogEvent(
            source=event.source,
            line=event.line,
            timestamp=event.timestamp,
            tags=tags,
        )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"TagRule(pattern={self.pattern!r}, tag={self.tag!r}, "
            f"value={self.value!r}, source={self.source!r})"
        )


@dataclass
class Tagger:
    """Applies a list of TagRules to log events in order."""

    _rules: List[TagRule] = field(default_factory=list)

    def add_rule(self, rule: TagRule) -> "Tagger":
        self._rules.append(rule)
        return self

    def apply(self, event: LogEvent) -> LogEvent:
        """Return the event with all matching tag rules applied."""
        for rule in self._rules:
            if rule.matches(event):
                event = rule.apply(event)
        return event

    @property
    def rules(self) -> List[TagRule]:
        return list(self._rules)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Tagger(rules={self._rules!r})"
