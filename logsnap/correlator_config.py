"""Load an EventCorrelator from a config dict or LogSnapConfig."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from logsnap.aggregator import LogEvent
from logsnap.correlator import CorrelationGroup, EventCorrelator


def _noop_flush(group: CorrelationGroup) -> None:  # pragma: no cover
    pass


def correlator_from_dict(
    cfg: Optional[Dict[str, Any]],
    on_flush: Callable[[CorrelationGroup], None] = _noop_flush,
) -> Optional[EventCorrelator]:
    """Build an EventCorrelator from a mapping, or return None if cfg is empty.

    Expected keys:
        pattern        (str, required) – regex with optional capture group for key
        window_seconds (float, default 5.0)
        max_size       (int,   default 100)
    """
    if not cfg:
        return None
    pattern = cfg.get("pattern")
    if not pattern:
        raise ValueError("correlator config requires a 'pattern' key")
    return EventCorrelator(
        pattern=pattern,
        on_flush=on_flush,
        window_seconds=float(cfg.get("window_seconds", 5.0)),
        max_size=int(cfg.get("max_size", 100)),
    )


def correlator_from_config(
    config: Any,
    on_flush: Callable[[CorrelationGroup], None] = _noop_flush,
) -> Optional[EventCorrelator]:
    """Build an EventCorrelator from a LogSnapConfig object."""
    raw = getattr(config, "correlator", None)
    return correlator_from_dict(raw, on_flush=on_flush)
