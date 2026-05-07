"""Event routing: dispatch LogEvents to named output channels based on rules."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from logsnap.aggregator import LogEvent


@dataclass
class RouteRule:
    """A single routing rule: if *pattern* matches the line, send to *channel*."""

    channel: str
    pattern: Optional[str] = None
    source: Optional[str] = None
    _regex: Optional[re.Pattern] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.pattern:
            self._regex = re.compile(self.pattern)

    def matches(self, event: LogEvent) -> bool:
        if self.source and event.source != self.source:
            return False
        if self._regex and not self._regex.search(event.line):
            return False
        return True

    def __repr__(self) -> str:
        return (
            f"RouteRule(channel={self.channel!r}, pattern={self.pattern!r}, "
            f"source={self.source!r})"
        )


Handler = Callable[[LogEvent], None]


class EventRouter:
    """Routes events to registered channel handlers based on ordered rules.

    The first matching rule wins.  If no rule matches, the event is sent to
    the *default* channel (if a handler is registered for it).
    """

    DEFAULT_CHANNEL = "default"

    def __init__(self) -> None:
        self._rules: List[RouteRule] = []
        self._handlers: Dict[str, List[Handler]] = {}

    def add_rule(self, rule: RouteRule) -> None:
        self._rules.append(rule)

    def register(self, channel: str, handler: Handler) -> None:
        self._handlers.setdefault(channel, []).append(handler)

    def route(self, event: LogEvent) -> str:
        """Return the channel name the event was dispatched to."""
        for rule in self._rules:
            if rule.matches(event):
                self._dispatch(rule.channel, event)
                return rule.channel
        self._dispatch(self.DEFAULT_CHANNEL, event)
        return self.DEFAULT_CHANNEL

    def _dispatch(self, channel: str, event: LogEvent) -> None:
        for handler in self._handlers.get(channel, []):
            handler(event)

    def __repr__(self) -> str:
        return f"EventRouter(rules={len(self._rules)}, channels={list(self._handlers)})"
