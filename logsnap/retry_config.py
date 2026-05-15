"""Load RetryPolicy / RetryEmitter from config dicts."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from logsnap.retry import RetryEmitter, RetryPolicy


def policy_from_dict(data: Optional[Dict[str, Any]]) -> RetryPolicy:
    """Build a RetryPolicy from a config mapping.

    Accepted keys: max_attempts, base_delay, backoff_factor, max_delay.
    Missing keys fall back to RetryPolicy defaults.
    """
    if not data:
        return RetryPolicy()
    return RetryPolicy(
        max_attempts=int(data.get("max_attempts", 3)),
        base_delay=float(data.get("base_delay", 0.5)),
        backoff_factor=float(data.get("backoff_factor", 2.0)),
        max_delay=float(data.get("max_delay", 10.0)),
    )


def emitter_from_dict(
    emit: Callable[[str], None],
    data: Optional[Dict[str, Any]],
) -> RetryEmitter:
    """Build a RetryEmitter wrapping *emit* using config in *data*."""
    policy = policy_from_dict(data)
    return RetryEmitter(emit=emit, policy=policy)


def emitter_from_config(
    emit: Callable[[str], None],
    config: Any,
) -> RetryEmitter:
    """Build a RetryEmitter from a LogSnapConfig object.

    Looks for config.retry (a dict or None).
    """
    raw: Optional[Dict[str, Any]] = getattr(config, "retry", None)
    return emitter_from_dict(emit, raw)
