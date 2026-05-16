"""Build a :class:`Masker` from configuration dicts."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from logsnap.masker import MaskRule, Masker

# Built-in patterns keyed by short name.
_BUILTINS: Dict[str, str] = {
    "credit_card": r"(?P<value>\b(?:\d[ -]?){13,16}\b)",
    "email": r"(?P<value>[\w.+-]+@[\w-]+\.[\w.]+)",
    "ipv4": r"(?P<value>\b(?:\d{1,3}\.){3}\d{1,3}\b)",
    "bearer_token": r"(?i)(?:Bearer\s+)(?P<value>[A-Za-z0-9\-._~+/]+=*)",
    "basic_auth": r"(?i)(?:Authorization:\s*Basic\s+)(?P<value>[A-Za-z0-9+/=]+)",
}


def _rule_from_dict(d: Dict[str, Any]) -> MaskRule:
    builtin = d.get("builtin")
    if builtin:
        if builtin not in _BUILTINS:
            raise ValueError(
                f"Unknown built-in mask rule {builtin!r}. "
                f"Available: {sorted(_BUILTINS)}"
            )
        pattern_str = _BUILTINS[builtin]
        label = builtin
    else:
        pattern_str = d["pattern"]
        label = d.get("label", "")

    flags = re.IGNORECASE if d.get("ignore_case") else 0
    compiled = re.compile(pattern_str, flags)
    mask = d.get("mask", "***")
    return MaskRule(pattern=compiled, mask=mask, label=label)


def masker_from_dict(rules_cfg: Optional[List[Dict[str, Any]]]) -> Masker:
    masker = Masker()
    if not rules_cfg:
        return masker
    for entry in rules_cfg:
        masker.add_rule(_rule_from_dict(entry))
    return masker


def masker_from_config(cfg: Any) -> Masker:
    """Extract masking config from a :class:`LogSnapConfig`-like object."""
    raw = getattr(cfg, "masking", None)
    if raw is None:
        return Masker()
    return masker_from_dict(raw if isinstance(raw, list) else raw.get("rules"))
