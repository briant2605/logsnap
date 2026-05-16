"""Load an EventSplitter from configuration."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from logsnap.splitter import EventSplitter


def splitter_from_dict(cfg: Optional[Dict[str, Any]]) -> Optional[EventSplitter]:
    """Return an EventSplitter configured from *cfg*, or None.

    Expected config shape (all keys optional)::

        splitter:
          maxsize: 1000   # internal queue depth (0 = unbounded)

    Returns ``None`` when *cfg* is ``None`` or empty so callers can skip
    wiring the splitter into the pipeline entirely.
    """
    if not cfg:
        return None
    maxsize = int(cfg.get("maxsize", 0))
    return EventSplitter(maxsize=maxsize)


def splitter_from_config(config: Any) -> Optional[EventSplitter]:
    """Convenience wrapper that accepts a :class:`~logsnap.config.LogSnapConfig`.

    Looks for a ``splitter`` key in the raw config dict.
    """
    raw: Optional[Dict[str, Any]] = None
    if hasattr(config, "to_dict"):
        raw = config.to_dict().get("splitter")
    elif isinstance(config, dict):
        raw = config.get("splitter")
    return splitter_from_dict(raw)
