"""Tests for logsnap.ratelimit_config."""

from __future__ import annotations

import pytest

from logsnap.ratelimit_config import throttle_manager_from_dict, throttle_manager_from_config
from logsnap.throttle import ThrottleManager


# ---------------------------------------------------------------------------
# throttle_manager_from_dict
# ---------------------------------------------------------------------------

def test_none_config_returns_default_manager():
    mgr = throttle_manager_from_dict(None)
    assert isinstance(mgr, ThrottleManager)


def test_empty_dict_returns_manager_with_default_rate():
    mgr = throttle_manager_from_dict({}, default_rate=50.0)
    # default_rate propagated — allow() should work without raising
    assert mgr.allow("any.log") is True


def test_default_rate_from_dict():
    mgr = throttle_manager_from_dict({"default_rate": 0})
    # rate=0 means every call is denied
    assert mgr.allow("x.log") is False


def test_source_rate_applied():
    cfg = {
        "default_rate": 1000,
        "sources": [
            {"source": "blocked.log", "rate": 0},
        ],
    }
    mgr = throttle_manager_from_dict(cfg)
    # blocked.log should be throttled immediately at rate=0
    assert mgr.allow("blocked.log") is False
    # other sources use high default rate
    assert mgr.allow("other.log") is True


def test_burst_parameter_accepted():
    cfg = {
        "sources": [
            {"source": "app.log", "rate": 10, "burst": 5},
        ]
    }
    mgr = throttle_manager_from_dict(cfg)
    # First 5 calls should be allowed (burst=5)
    results = [mgr.allow("app.log") for _ in range(5)]
    assert all(results)
    # 6th call should be denied (burst exhausted, refill too slow)
    assert mgr.allow("app.log") is False


def test_missing_source_key_raises():
    with pytest.raises(ValueError, match="source"):
        throttle_manager_from_dict({"sources": [{"rate": 10}]})


def test_missing_rate_key_raises():
    with pytest.raises(ValueError, match="rate"):
        throttle_manager_from_dict({"sources": [{"source": "a.log"}]})


def test_negative_rate_raises():
    with pytest.raises(ValueError, match="rate"):
        throttle_manager_from_dict({"sources": [{"source": "a.log", "rate": -1}]})


def test_burst_less_than_one_raises():
    with pytest.raises(ValueError, match="burst"):
        throttle_manager_from_dict(
            {"sources": [{"source": "a.log", "rate": 10, "burst": 0}]}
        )


# ---------------------------------------------------------------------------
# throttle_manager_from_config
# ---------------------------------------------------------------------------

class _FakeConfig:
    def __init__(self, rate_limit):
        self.rate_limit = rate_limit


def test_from_config_with_dict():
    config = _FakeConfig({"default_rate": 0, "sources": []})
    mgr = throttle_manager_from_config(config)
    assert isinstance(mgr, ThrottleManager)
    assert mgr.allow("x.log") is False  # default_rate=0


def test_from_config_missing_attribute():
    class _Bare:
        pass

    mgr = throttle_manager_from_config(_Bare())
    assert isinstance(mgr, ThrottleManager)
    assert mgr.allow("anything") is True  # default permissive


def test_from_config_none_rate_limit():
    config = _FakeConfig(None)
    mgr = throttle_manager_from_config(config)
    assert mgr.allow("x.log") is True
