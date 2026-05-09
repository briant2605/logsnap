"""Load an Enricher from configuration dicts or a LogSnapConfig object."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from logsnap.enricher import EnrichRule, Enricher


def _rule_from_dict(d: Dict[str, Any]) -> EnrichRule:
    """Build a single :class:`EnrichRule` from a mapping.

    Expected keys:
        - ``pattern``  (str, required)  – regex applied to the log line.
        - ``tag``      (str, required)  – metadata key to set on the event.
        - ``value``    (any, optional)  – value stored under *tag*; defaults to
          ``True`` when omitted.
        - ``source``   (str, optional)  – restrict the rule to a specific log
          source name.  ``None`` means *all sources*.

    Raises:
        KeyError: if ``pattern`` or ``tag`` are missing.
    """
    pattern: str = d["pattern"]
    tag: str = d["tag"]
    value: Any = d.get("value", True)
    source: Optional[str] = d.get("source", None)
    return EnrichRule(pattern=pattern, tag=tag, value=value, source=source)


def enricher_from_dict(
    rules: Optional[List[Dict[str, Any]]],
) -> Enricher:
    """Build an :class:`Enricher` from a list of rule dicts.

    Args:
        rules: A list of rule mappings as returned by a YAML/JSON parser, or
               ``None`` / an empty list to get a no-op enricher.

    Returns:
        A configured :class:`Enricher` instance.
    """
    enricher = Enricher()
    if not rules:
        return enricher
    for raw in rules:
        enricher.add_rule(_rule_from_dict(raw))
    return enricher


def enricher_from_config(config: Any) -> Enricher:
    """Build an :class:`Enricher` from a :class:`~logsnap.config.LogSnapConfig`.

    The config object is expected to expose an ``enrich`` attribute that is
    either ``None`` or a list of rule dicts (matching the schema described in
    :func:`_rule_from_dict`).

    Args:
        config: A :class:`~logsnap.config.LogSnapConfig` instance.

    Returns:
        A configured :class:`Enricher` instance.
    """
    raw_rules: Optional[List[Dict[str, Any]]] = getattr(config, "enrich", None)
    return enricher_from_dict(raw_rules)
