"""Pattern-based log line redaction for sensitive data masking."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RedactRule:
    """A single redaction rule: matches a regex pattern and replaces it."""

    name: str
    pattern: re.Pattern
    replacement: str = "[REDACTED]"

    def apply(self, line: str) -> str:
        """Return line with all matches replaced."""
        return self.pattern.sub(self.replacement, line)

    def __repr__(self) -> str:  # pragma: no cover
        return f"RedactRule(name={self.name!r}, pattern={self.pattern.pattern!r})"


class Redactor:
    """Applies an ordered list of RedactRules to log lines."""

    # Built-in presets for common sensitive patterns
    PRESETS: dict[str, tuple[str, str]] = {
        "ipv4": (
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "[IP]",
        ),
        "email": (
            r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
            "[EMAIL]",
        ),
        "bearer_token": (
            r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]+=*",
            "Bearer [REDACTED]",
        ),
        "credit_card": (
            r"\b(?:\d[ -]?){13,16}\b",
            "[CARD]",
        ),
    }

    def __init__(self, rules: Optional[List[RedactRule]] = None) -> None:
        self._rules: List[RedactRule] = rules or []

    @classmethod
    def from_presets(cls, names: List[str]) -> "Redactor":
        """Build a Redactor from named built-in presets."""
        rules = []
        for name in names:
            if name not in cls.PRESETS:
                raise ValueError(f"Unknown redaction preset: {name!r}")
            pattern_str, replacement = cls.PRESETS[name]
            rules.append(
                RedactRule(
                    name=name,
                    pattern=re.compile(pattern_str),
                    replacement=replacement,
                )
            )
        return cls(rules=rules)

    def add_rule(self, name: str, pattern: str, replacement: str = "[REDACTED]") -> None:
        """Add a custom redaction rule."""
        self._rules.append(
            RedactRule(name=name, pattern=re.compile(pattern), replacement=replacement)
        )

    def redact(self, line: str) -> str:
        """Apply all rules in order and return the redacted line."""
        for rule in self._rules:
            line = rule.apply(line)
        return line

    @property
    def rules(self) -> List[RedactRule]:
        return list(self._rules)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Redactor(rules={self._rules!r})"
