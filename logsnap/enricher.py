"""Field enrichment: attach extra key/value metadata to LogEvents before emission."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from logsnap.aggregator import LogEvent


@dataclass
class EnrichRule:
    """A single enrichment rule that adds a tag when a pattern matches the line."""

    tag: str
    pattern: str
    value: str = "true"
    _regex: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._regex = re.compile(self.pattern)

    def apply(self, event: LogEvent) -> LogEvent:
        """Return the event (mutated in-place) with the tag added if pattern matches."""
        if self._regex.search(event.line):
            event.extra[self.tag] = self.value
        return event

    def __repr__(self) -> str:
        return f"EnrichRule(tag={self.tag!r}, pattern={self.pattern!r}, value={self.value!r})"


class Enricher:
    """Applies an ordered list of EnrichRules to every LogEvent."""

    def __init__(self, rules: Optional[List[EnrichRule]] = None) -> None:
        self._rules: List[EnrichRule] = list(rules or [])

    def add_rule(self, rule: EnrichRule) -> None:
        self._rules.append(rule)

    def enrich(self, event: LogEvent) -> LogEvent:
        """Apply all rules to *event* and return it."""
        for rule in self._rules:
            rule.apply(event)
        return event

    @property
    def rules(self) -> List[EnrichRule]:
        return list(self._rules)

    def __repr__(self) -> str:
        return f"Enricher(rules={self._rules!r})"


def enricher_from_dict(cfg: Optional[List[Dict]] ) -> Enricher:
    """Build an Enricher from a list of rule dicts (e.g. loaded from YAML/JSON config).

    Each dict must have 'tag' and 'pattern'; 'value' is optional (defaults to 'true').
    """
    if not cfg:
        return Enricher()
    rules = [
        EnrichRule(
            tag=entry["tag"],
            pattern=entry["pattern"],
            value=entry.get("value", "true"),
        )
        for entry in cfg
    ]
    return Enricher(rules)
