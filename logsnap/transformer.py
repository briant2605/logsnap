"""Line transformation: apply a chain of string transformations to log lines."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class TransformRule:
    """A single named transformation applied to a log line."""

    name: str
    _fn: Callable[[str], str] = field(repr=False)

    def apply(self, line: str) -> str:
        return self._fn(line)

    def __repr__(self) -> str:  # pragma: no cover
        return f"TransformRule(name={self.name!r})"


class LineTransformer:
    """Applies an ordered chain of TransformRules to each line."""

    def __init__(self, rules: Optional[List[TransformRule]] = None) -> None:
        self._rules: List[TransformRule] = list(rules or [])

    def add_rule(self, rule: TransformRule) -> None:
        self._rules.append(rule)

    def transform(self, line: str) -> str:
        for rule in self._rules:
            line = rule.apply(line)
        return line

    @property
    def rules(self) -> List[TransformRule]:
        return list(self._rules)

    def __repr__(self) -> str:  # pragma: no cover
        return f"LineTransformer(rules={self._rules!r})"


# ---------------------------------------------------------------------------
# Built-in factory helpers
# ---------------------------------------------------------------------------

def strip_ansi_rule() -> TransformRule:
    """Remove ANSI escape sequences from a line."""
    _ansi_re = re.compile(r"\x1b\[[0-9;]*[mGKHF]")

    def _apply(line: str) -> str:
        return _ansi_re.sub("", line)

    return TransformRule(name="strip_ansi", _fn=_apply)


def uppercase_rule() -> TransformRule:
    return TransformRule(name="uppercase", _fn=str.upper)


def lowercase_rule() -> TransformRule:
    return TransformRule(name="lowercase", _fn=str.lower)


def strip_whitespace_rule() -> TransformRule:
    return TransformRule(name="strip_whitespace", _fn=str.strip)


def regex_replace_rule(pattern: str, replacement: str, name: str = "regex_replace") -> TransformRule:
    """Replace all occurrences of *pattern* with *replacement*."""
    _re = re.compile(pattern)

    def _apply(line: str) -> str:
        return _re.sub(replacement, line)

    return TransformRule(name=name, _fn=_apply)
