"""Load a Tagger from a config dict or LogSnapConfig."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from logsnap.tagger import TagRule, Tagger


def _rule_from_dict(d: Dict[str, Any]) -> TagRule:
    pattern = d["pattern"]
    tag = d["tag"]
    value = d.get("value", True)
    source = d.get("source", None)
    return TagRule(pattern=pattern, tag=tag, value=value, source=source)


def tagger_from_dict(rules_cfg: Optional[List[Dict[str, Any]]]) -> Tagger:
    """Build a Tagger from a list of rule dicts.

    Returns an empty Tagger when *rules_cfg* is None or empty.
    """
    tagger = Tagger()
    if not rules_cfg:
        return tagger
    for entry in rules_cfg:
        tagger.add_rule(_rule_from_dict(entry))
    return tagger


def tagger_from_config(cfg: Any) -> Tagger:
    """Build a Tagger from a LogSnapConfig object.

    Reads ``cfg.tagging`` if present, otherwise returns an empty Tagger.
    """
    rules_cfg = getattr(cfg, "tagging", None)
    return tagger_from_dict(rules_cfg)
