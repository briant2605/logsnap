"""Build a LineTransformer from a config dict or LogSnapConfig."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from logsnap.transformer import (
    LineTransformer,
    TransformRule,
    lowercase_rule,
    regex_replace_rule,
    strip_ansi_rule,
    strip_whitespace_rule,
    uppercase_rule,
)

_BUILTIN: Dict[str, Any] = {
    "strip_ansi": strip_ansi_rule,
    "uppercase": uppercase_rule,
    "lowercase": lowercase_rule,
    "strip_whitespace": strip_whitespace_rule,
}


def _rule_from_dict(d: Dict[str, Any]) -> TransformRule:
    kind = d.get("type", "")
    if kind in _BUILTIN:
        return _BUILTIN[kind]()
    if kind == "regex_replace":
        pattern = d["pattern"]
        replacement = d.get("replacement", "")
        name = d.get("name", "regex_replace")
        return regex_replace_rule(pattern, replacement, name=name)
    raise ValueError(f"Unknown transform type: {kind!r}")


def transformer_from_dict(rules_cfg: Optional[List[Dict[str, Any]]]) -> LineTransformer:
    """Build a LineTransformer from a list of rule dicts."""
    if not rules_cfg:
        return LineTransformer()
    rules = [_rule_from_dict(r) for r in rules_cfg]
    return LineTransformer(rules=rules)


def transformer_from_config(config: Any) -> LineTransformer:
    """Extract transform rules from a LogSnapConfig (or any object with .to_dict())."""
    raw: Dict[str, Any] = config.to_dict() if hasattr(config, "to_dict") else {}
    return transformer_from_dict(raw.get("transforms"))
