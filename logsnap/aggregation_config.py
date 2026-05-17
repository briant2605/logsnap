"""Load EventAggregator from config dict or LogSnapConfig."""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

from logsnap.aggregation import AggregationBucket, EventAggregator


def _key_fn_from_dict(cfg: dict) -> Callable[[str, str], str]:
    """Build a key function from config.

    Supported strategies:
      - ``source``: key is just the source path.
      - ``pattern``: key is the first capture group of a regex match, or the
        full line if there is no match.
    """
    strategy = cfg.get("strategy", "source")
    if strategy == "source":
        return lambda source, line: source
    if strategy == "pattern":
        raw = cfg.get("pattern")
        if not raw:
            raise ValueError("aggregation key strategy 'pattern' requires 'pattern'")
        rx = re.compile(raw)

        def _pattern_key(source: str, line: str) -> str:
            m = rx.search(line)
            if m and m.lastindex:
                return m.group(1)
            return line

        return _pattern_key
    raise ValueError(f"Unknown aggregation key strategy: {strategy!r}")


def aggregator_from_dict(
    cfg: Optional[Dict[str, Any]],
    on_flush: Optional[Callable[[List[AggregationBucket]], None]] = None,
) -> Optional[EventAggregator]:
    if not cfg:
        return None
    key_cfg = cfg.get("key", {"strategy": "source"})
    key_fn = _key_fn_from_dict(key_cfg)
    flush_interval = float(cfg.get("flush_interval", 60.0))
    max_samples = int(cfg.get("max_samples", 3))
    return EventAggregator(
        key_fn=key_fn,
        flush_interval=flush_interval,
        on_flush=on_flush,
        max_samples=max_samples,
    )


def aggregator_from_config(
    config: Any,
    on_flush: Optional[Callable[[List[AggregationBucket]], None]] = None,
) -> Optional[EventAggregator]:
    raw = getattr(config, "aggregation", None)
    return aggregator_from_dict(raw, on_flush=on_flush)
