"""Line normalizer: apply a sequence of normalization steps to log lines."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class NormalizeRule:
    """A single normalization step: a named transform applied to a line."""

    name: str
    _fn: Callable[[str], str] = field(repr=False)

    def apply(self, line: str) -> str:
        return self._fn(line)

    def __repr__(self) -> str:  # pragma: no cover
        return f"NormalizeRule(name={self.name!r})"


# ---------------------------------------------------------------------------
# Built-in normalization functions
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(line: str) -> str:
    return _ANSI_RE.sub("", line)


def _strip_whitespace(line: str) -> str:
    return line.strip()


def _collapse_whitespace(line: str) -> str:
    return re.sub(r"[ \t]+", " ", line)


def _to_lowercase(line: str) -> str:
    return line.lower()


def _to_uppercase(line: str) -> str:
    return line.upper()


_BUILTINS: dict[str, Callable[[str], str]] = {
    "strip_ansi": _strip_ansi,
    "strip_whitespace": _strip_whitespace,
    "collapse_whitespace": _collapse_whitespace,
    "lowercase": _to_lowercase,
    "uppercase": _to_uppercase,
}


class LineNormalizer:
    """Applies an ordered list of NormalizeRules to a log line."""

    def __init__(self) -> None:
        self._rules: List[NormalizeRule] = []

    # ------------------------------------------------------------------
    def add_rule(self, rule: NormalizeRule) -> None:
        self._rules.append(rule)

    @classmethod
    def from_names(cls, names: List[str]) -> "LineNormalizer":
        """Construct a normalizer from a list of built-in step names."""
        normalizer = cls()
        for name in names:
            if name not in _BUILTINS:
                raise ValueError(
                    f"Unknown normalization step {name!r}. "
                    f"Available: {sorted(_BUILTINS)}"
                )
            normalizer.add_rule(NormalizeRule(name=name, _fn=_BUILTINS[name]))
        return normalizer

    # ------------------------------------------------------------------
    def normalize(self, line: str) -> str:
        for rule in self._rules:
            line = rule.apply(line)
        return line

    def __len__(self) -> int:
        return len(self._rules)

    def __repr__(self) -> str:  # pragma: no cover
        return f"LineNormalizer(rules={self._rules!r})"
