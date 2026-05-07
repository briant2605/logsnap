"""Load an EventRouter from a config dict or LogSnapConfig object."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from logsnap.routing import EventRouter, RouteRule


def _rule_from_dict(data: Dict[str, Any]) -> RouteRule:
    channel = data.get("channel")
    if not channel:
        raise ValueError("Each routing rule must specify a 'channel'.")
    return RouteRule(
        channel=channel,
        pattern=data.get("pattern"),
        source=data.get("source"),
    )


def router_from_dict(cfg: Optional[Dict[str, Any]]) -> EventRouter:
    """Build an EventRouter from a plain dict (e.g. parsed YAML/JSON).

    Expected shape::

        routing:
          rules:
            - channel: errors
              pattern: "ERROR|CRITICAL"
            - channel: auth
              source: auth.log
    """
    router = EventRouter()
    if not cfg:
        return router
    rules: List[Dict[str, Any]] = cfg.get("rules", [])
    for rule_data in rules:
        router.add_rule(_rule_from_dict(rule_data))
    return router


def router_from_config(config: Any) -> EventRouter:
    """Build an EventRouter from a LogSnapConfig instance."""
    raw = config.to_dict()
    return router_from_dict(raw.get("routing"))
