"""Load ThrottleManager configuration from a dict or config object."""

from __future__ import annotations

from typing import Any, Dict, Optional

from logsnap.throttle import ThrottleManager


def _bucket_from_dict(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalise a single rate-limit bucket definition."""
    source = entry.get("source")
    if not source or not isinstance(source, str):
        raise ValueError("Each rate-limit entry must have a non-empty 'source' string.")

    rate = entry.get("rate")
    if rate is None:
        raise ValueError(f"Rate-limit entry for '{source}' is missing 'rate'.")
    rate = float(rate)
    if rate < 0:
        raise ValueError(f"'rate' for '{source}' must be >= 0, got {rate}.")

    burst = entry.get("burst")
    if burst is not None:
        burst = int(burst)
        if burst < 1:
            raise ValueError(f"'burst' for '{source}' must be >= 1, got {burst}.")

    return {"source": source, "rate": rate, "burst": burst}


def throttle_manager_from_dict(
    cfg: Optional[Dict[str, Any]],
    default_rate: float = 0.0,
) -> ThrottleManager:
    """Build a :class:`ThrottleManager` from a mapping.

    Expected shape::

        {
            "default_rate": 100,        # lines/sec applied to unknown sources
            "sources": [
                {"source": "app.log", "rate": 50, "burst": 200},
                {"source": "err.log", "rate": 10},
            ]
        }

    ``burst`` defaults to ``rate`` when omitted (handled inside ThrottleManager).
    """
    if not cfg:
        return ThrottleManager(default_rate=default_rate)

    resolved_default = float(cfg.get("default_rate", default_rate))
    manager = ThrottleManager(default_rate=resolved_default)

    for entry in cfg.get("sources", []):
        bucket = _bucket_from_dict(entry)
        kwargs: Dict[str, Any] = {"rate": bucket["rate"]}
        if bucket["burst"] is not None:
            kwargs["burst"] = bucket["burst"]
        manager.set_source_rate(bucket["source"], **kwargs)

    return manager


def throttle_manager_from_config(config: Any) -> ThrottleManager:
    """Build a :class:`ThrottleManager` from a :class:`LogSnapConfig` instance."""
    raw = getattr(config, "rate_limit", None)
    if isinstance(raw, dict):
        return throttle_manager_from_dict(raw)
    return ThrottleManager(default_rate=0.0)
