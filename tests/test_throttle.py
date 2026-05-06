"""Tests for logsnap.throttle.ThrottleManager."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from logsnap.throttle import ThrottleManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mono(value: float):
    """Patch time.monotonic to return a fixed value."""
    return patch("logsnap.throttle.time.monotonic", return_value=value)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_no_rate_always_allows():
    tm = ThrottleManager(rate=None)
    for _ in range(1000):
        assert tm.allow("app") is True


def test_zero_rate_always_allows():
    tm = ThrottleManager(rate=0)
    assert tm.allow("app") is True


def test_rate_allows_up_to_burst():
    with _mono(0.0):
        tm = ThrottleManager(rate=5, burst=5)
        results = [tm.allow("app") for _ in range(7)]

    assert results[:5] == [True] * 5
    assert results[5:] == [False, False]


def test_tokens_refill_over_time():
    tm = ThrottleManager(rate=10, burst=10)

    # Drain the bucket completely at t=0
    with _mono(0.0):
        for _ in range(10):
            tm.allow("app")
        assert tm.allow("app") is False

    # After 0.5 s, 5 new tokens should be available (rate=10 lines/s)
    with _mono(0.5):
        results = [tm.allow("app") for _ in range(6)]

    assert results[:5] == [True] * 5
    assert results[5] is False


def test_separate_sources_independent():
    with _mono(0.0):
        tm = ThrottleManager(rate=2, burst=2)
        assert tm.allow("web") is True
        assert tm.allow("web") is True
        assert tm.allow("web") is False  # web exhausted

        # db source still has a full bucket
        assert tm.allow("db") is True
        assert tm.allow("db") is True
        assert tm.allow("db") is False


def test_reset_restores_full_bucket():
    with _mono(0.0):
        tm = ThrottleManager(rate=3, burst=3)
        for _ in range(3):
            tm.allow("app")
        assert tm.allow("app") is False

    tm.reset("app")

    with _mono(0.0):
        assert tm.allow("app") is True


def test_stats_returns_current_tokens():
    with _mono(0.0):
        tm = ThrottleManager(rate=4, burst=4)
        tm.allow("app")
        tm.allow("app")

    with _mono(0.0):
        s = tm.stats("app")

    assert s["tokens"] == pytest.approx(2.0)
    assert s["rate"] == pytest.approx(4.0)


def test_stats_unknown_source_returns_full_burst():
    tm = ThrottleManager(rate=10, burst=10)
    s = tm.stats("unknown")
    assert s["tokens"] == pytest.approx(10.0)
