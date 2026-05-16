"""Field masking: replace sensitive field values in structured log events."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MaskRule:
    """Replace a named capture group's value with a mask string."""

    pattern: re.Pattern
    mask: str = "***"
    label: str = ""

    def apply(self, line: str) -> str:
        """Return *line* with all matches replaced by *mask*."""

        def _replace(m: re.Match) -> str:  # type: ignore[type-arg]
            full = m.group(0)
            try:
                value = m.group("value")
                return full.replace(value, self.mask, 1)
            except IndexError:
                return self.mask

        return self.pattern.sub(_replace, line)

    def __repr__(self) -> str:
        label = self.label or self.pattern.pattern
        return f"MaskRule({label!r}, mask={self.mask!r})"


class Masker:
    """Apply an ordered list of :class:`MaskRule` objects to a line."""

    def __init__(self, rules: Optional[List[MaskRule]] = None) -> None:
        self._rules: List[MaskRule] = list(rules or [])

    def add_rule(self, rule: MaskRule) -> None:
        self._rules.append(rule)

    def apply(self, line: str) -> str:
        for rule in self._rules:
            line = rule.apply(line)
        return line

    def stats(self) -> Dict[str, Any]:
        return {"rules": [repr(r) for r in self._rules]}

    def __repr__(self) -> str:
        return f"Masker(rules={self._rules!r})"
