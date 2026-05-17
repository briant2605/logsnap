"""Load an :class:`EventClassifier` from a config dict or :class:`LogSnapConfig`."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from logsnap.classifier import ClassifyRule, EventClassifier


def _rule_from_dict(d: Dict[str, Any]) -> ClassifyRule:
    """Build a :class:`ClassifyRule` from a plain dict.

    Required keys: ``pattern``, ``category``.
    Optional key:  ``source``.
    """
    pattern = d["pattern"]
    category = d["category"]
    source: Optional[str] = d.get("source")
    return ClassifyRule(pattern=pattern, category=category, source=source)


def classifier_from_dict(
    data: Optional[List[Dict[str, Any]]],
    default_category: Optional[str] = None,
) -> Optional[EventClassifier]:
    """Return an :class:`EventClassifier` built from *data*, or ``None``.

    *data* is expected to be a list of rule dicts (as found under the
    ``classifier`` key of the logsnap YAML config).  Returns ``None`` when
    *data* is ``None`` or empty and no *default_category* is given.
    """
    if not data and default_category is None:
        return None

    classifier = EventClassifier(default_category=default_category)
    for item in data or []:
        classifier.add_rule(_rule_from_dict(item))
    return classifier


def classifier_from_config(config: Any) -> Optional[EventClassifier]:
    """Extract classifier settings from a :class:`LogSnapConfig` instance."""
    raw = getattr(config, "classifier", None)
    if raw is None:
        return None
    rules: List[Dict[str, Any]] = raw.get("rules") or []
    default_category: Optional[str] = raw.get("default_category")
    return classifier_from_dict(rules, default_category=default_category)
