"""Load a LineSampler from a config dict or LogSnapConfig."""
from __future__ import annotations

from typing import Any, Dict

from logsnap.sampling import LineSampler


def sampler_from_dict(cfg: Dict[str, Any]) -> LineSampler:
    """Build a LineSampler from a plain dict.

    Expected keys (all optional):
        rate (int, default 1) — keep 1 in every *rate* events.

    Example config section::

        sampling:
          rate: 10
    """
    sampling_cfg = cfg.get("sampling", {})
    rate = int(sampling_cfg.get("rate", 1))
    return LineSampler(rate=rate)


def sampler_from_config(config: Any) -> LineSampler:
    """Build a LineSampler from a LogSnapConfig instance.

    Falls back to rate=1 (no sampling) if the config carries no
    ``sampling`` section.
    """
    raw: Dict[str, Any] = config.to_dict() if hasattr(config, "to_dict") else {}
    return sampler_from_dict(raw)
