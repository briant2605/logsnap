"""Load alert rules from a logsnap config dict."""
from __future__ import annotations

from typing import Any, Dict, List

from logsnap.alerting import AlertManager, AlertRule


def _rule_from_dict(d: Dict[str, Any]) -> AlertRule:
    """Build an :class:`AlertRule` from a plain dict (e.g. parsed YAML/JSON)."""
    required = ("name", "source", "threshold", "window")
    missing = [k for k in required if k not in d]
    if missing:
        raise ValueError(f"Alert rule missing keys: {missing}")

    return AlertRule(
        name=str(d["name"]),
        source=str(d["source"]),
        threshold=int(d["threshold"]),
        window=float(d["window"]),
        cooldown=float(d.get("cooldown", 60.0)),
    )


def load_alert_manager(
    config: Dict[str, Any],
    handler=None,
) -> AlertManager:
    """Create an :class:`AlertManager` populated from *config*.

    Expected config shape::

        alerts:
          - name: high-errors
            source: "app.log"
            threshold: 10
            window: 30
            cooldown: 120
    """
    manager = AlertManager(handler=handler)
    rules_cfg: List[Dict[str, Any]] = config.get("alerts", []) or []
    for raw in rules_cfg:
        manager.add_rule(_rule_from_dict(raw))
    return manager
