"""Load MultilineConfig from a plain dict or a LogSnapConfig object."""
from __future__ import annotations

from typing import Any, Dict, Optional

from logsnap.multiline import MultilineConfig


def multiline_from_dict(raw: Optional[Dict[str, Any]]) -> Optional[MultilineConfig]:
    """Return a MultilineConfig built from *raw*, or None if raw is falsy."""
    if not raw:
        return None

    kwargs: Dict[str, Any] = {}

    if "start_pattern" in raw:
        kwargs["start_pattern"] = str(raw["start_pattern"])
    if "max_lines" in raw:
        value = int(raw["max_lines"])
        if value < 1:
            raise ValueError("multiline.max_lines must be >= 1")
        kwargs["max_lines"] = value
    if "flush_timeout" in raw:
        value_f = float(raw["flush_timeout"])
        if value_f < 0:
            raise ValueError("multiline.flush_timeout must be >= 0")
        kwargs["flush_timeout"] = value_f

    return MultilineConfig(**kwargs)


def multiline_from_config(cfg: Any) -> Optional[MultilineConfig]:
    """Extract multiline config from a LogSnapConfig instance."""
    raw = getattr(cfg, "multiline", None)
    if isinstance(raw, dict):
        return multiline_from_dict(raw)
    return None
