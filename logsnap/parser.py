"""Structured log line parser: extracts fields from log lines via named regex groups."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ParseRule:
    name: str
    pattern: re.Pattern
    defaults: Dict[str, str] = field(default_factory=dict)

    def apply(self, line: str) -> Optional[Dict[str, str]]:
        """Return a dict of named groups if the pattern matches, else None."""
        m = self.pattern.search(line)
        if m is None:
            return None
        result = dict(self.defaults)
        result.update({k: v for k, v in m.groupdict().items() if v is not None})
        return result

    def __repr__(self) -> str:  # pragma: no cover
        return f"ParseRule(name={self.name!r}, pattern={self.pattern.pattern!r})"


class LineParser:
    """Applies a list of ParseRules in order; returns fields from the first match."""

    def __init__(self) -> None:
        self._rules: List[ParseRule] = []

    def add_rule(self, rule: ParseRule) -> None:
        self._rules.append(rule)

    def parse(self, line: str) -> Dict[str, str]:
        """Return extracted fields, or {'raw': line} if no rule matches."""
        for rule in self._rules:
            fields = rule.apply(line)
            if fields is not None:
                fields.setdefault("_rule", rule.name)
                return fields
        return {"raw": line}

    @property
    def rules(self) -> List[ParseRule]:
        return list(self._rules)

    def __repr__(self) -> str:  # pragma: no cover
        return f"LineParser(rules={self._rules!r})"
