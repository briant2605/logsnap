"""Simple threshold-based alerting for logsnap pipelines."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional


@dataclass
class AlertRule:
    """Fires when *source* exceeds *threshold* matched lines within *window* seconds."""

    name: str
    source: str          # glob or exact source tag; "*" matches all
    threshold: int       # matched lines in window before alert fires
    window: float        # rolling window in seconds
    cooldown: float = 60.0  # seconds between repeated alerts for same rule

    # internal state
    _timestamps: list = field(default_factory=list, repr=False)
    _last_fired: float = field(default=0.0, repr=False)

    def record(self, ts: float) -> bool:
        """Record a matched line at *ts*; return True if alert should fire."""
        cutoff = ts - self.window
        self._timestamps = [t for t in self._timestamps if t >= cutoff]
        self._timestamps.append(ts)

        if len(self._timestamps) >= self.threshold:
            if ts - self._last_fired >= self.cooldown:
                self._last_fired = ts
                self._timestamps.clear()
                return True
        return False


AlertHandler = Callable[[AlertRule, float], None]


class AlertManager:
    """Manages a collection of :class:`AlertRule` objects and dispatches alerts."""

    def __init__(self, handler: Optional[AlertHandler] = None) -> None:
        self._rules: Dict[str, AlertRule] = {}
        self._handler: AlertHandler = handler or _default_handler

    def add_rule(self, rule: AlertRule) -> None:
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> None:
        self._rules.pop(name, None)

    def notify(self, source: str, ts: Optional[float] = None) -> None:
        """Called for every matched line; *source* is the file tag."""
        ts = ts if ts is not None else time.monotonic()
        for rule in self._rules.values():
            if rule.source not in (source, "*"):
                continue
            if rule.record(ts):
                self._handler(rule, ts)

    def rules(self) -> list:
        return list(self._rules.values())


def _default_handler(rule: AlertRule, ts: float) -> None:  # pragma: no cover
    print(f"[ALERT] rule={rule.name!r} source={rule.source!r} at t={ts:.3f}")
