"""Tests for logsnap.retry_config."""
import pytest

from logsnap.retry import RetryPolicy
from logsnap.retry_config import emitter_from_config, emitter_from_dict, policy_from_dict


# ---------------------------------------------------------------------------
# policy_from_dict
# ---------------------------------------------------------------------------

def test_none_returns_default_policy():
    p = policy_from_dict(None)
    assert isinstance(p, RetryPolicy)
    assert p.max_attempts == 3


def test_empty_dict_returns_default_policy():
    p = policy_from_dict({})
    assert p.max_attempts == 3
    assert p.base_delay == 0.5


def test_custom_values_loaded():
    p = policy_from_dict(
        {"max_attempts": 5, "base_delay": 0.1, "backoff_factor": 3.0, "max_delay": 30.0}
    )
    assert p.max_attempts == 5
    assert p.base_delay == 0.1
    assert p.backoff_factor == 3.0
    assert p.max_delay == 30.0


def test_partial_dict_uses_defaults_for_missing_keys():
    p = policy_from_dict({"max_attempts": 10})
    assert p.max_attempts == 10
    assert p.base_delay == 0.5  # default


# ---------------------------------------------------------------------------
# emitter_from_dict
# ---------------------------------------------------------------------------

def test_emitter_from_dict_wraps_callable():
    received: list[str] = []
    emitter = emitter_from_dict(received.append, {"max_attempts": 1})
    emitter.emit("hi")
    assert received == ["hi"]


def test_emitter_from_dict_none_uses_defaults():
    received: list[str] = []
    emitter = emitter_from_dict(received.append, None)
    assert emitter._policy.max_attempts == 3


# ---------------------------------------------------------------------------
# emitter_from_config
# ---------------------------------------------------------------------------

class _FakeConfig:
    def __init__(self, retry=None):
        self.retry = retry


def test_emitter_from_config_no_retry_attr():
    received: list[str] = []
    emitter = emitter_from_config(received.append, _FakeConfig(retry=None))
    assert emitter._policy.max_attempts == 3


def test_emitter_from_config_reads_retry_dict():
    received: list[str] = []
    cfg = _FakeConfig(retry={"max_attempts": 7, "base_delay": 0.0})
    emitter = emitter_from_config(received.append, cfg)
    assert emitter._policy.max_attempts == 7


def test_emitter_from_config_missing_attr_uses_defaults():
    """Config objects without a 'retry' attribute fall back gracefully."""
    received: list[str] = []

    class Bare:
        pass

    emitter = emitter_from_config(received.append, Bare())
    assert emitter._policy.base_delay == 0.5
