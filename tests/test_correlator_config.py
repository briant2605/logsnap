"""Tests for logsnap.correlator_config."""
from __future__ import annotations

from typing import List

import pytest

from logsnap.aggregator import LogEvent
from logsnap.correlator import CorrelationGroup
from logsnap.correlator_config import correlator_from_config, correlator_from_dict


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _event(line: str) -> LogEvent:
    return LogEvent(source="svc.log", line=line)


class _FakeConfig:
    def __init__(self, correlator=None):
        self.correlator = correlator


# ---------------------------------------------------------------------------
# correlator_from_dict
# ---------------------------------------------------------------------------

def test_none_returns_none():
    assert correlator_from_dict(None) is None


def test_empty_dict_returns_none():
    assert correlator_from_dict({}) is None


def test_missing_pattern_raises():
    with pytest.raises(ValueError, match="pattern"):
        correlator_from_dict({"window_seconds": 3})


def test_valid_config_builds_correlator():
    flushed: List[CorrelationGroup] = []
    c = correlator_from_dict(
        {"pattern": r"id=(\w+)", "window_seconds": 10.0, "max_size": 50},
        on_flush=flushed.append,
    )
    assert c is not None
    c.record(_event("id=abc hello"))
    c.flush_all()
    assert len(flushed) == 1
    assert flushed[0].key == "abc"


def test_defaults_applied_when_omitted():
    c = correlator_from_dict({"pattern": r"req=(\w+)"})
    # just verify it constructs without error using defaults
    assert c is not None


def test_window_and_max_size_forwarded():
    flushed: List[CorrelationGroup] = []
    c = correlator_from_dict(
        {"pattern": r"t=(\d+)", "max_size": 2},
        on_flush=flushed.append,
    )
    c.record(_event("t=1 a"))
    c.record(_event("t=1 b"))
    # max_size=2 should have triggered flush automatically
    assert len(flushed) == 1


# ---------------------------------------------------------------------------
# correlator_from_config
# ---------------------------------------------------------------------------

def test_from_config_none_attr_returns_none():
    assert correlator_from_config(_FakeConfig(correlator=None)) is None


def test_from_config_builds_correlator():
    flushed: List[CorrelationGroup] = []
    cfg = _FakeConfig(correlator={"pattern": r"job=(\w+)"})
    c = correlator_from_config(cfg, on_flush=flushed.append)
    assert c is not None
    c.record(_event("job=export started"))
    c.flush_all()
    assert flushed[0].key == "export"
