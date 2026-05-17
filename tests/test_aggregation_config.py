"""Tests for logsnap.aggregation_config."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from logsnap.aggregation import EventAggregator
from logsnap.aggregation_config import aggregator_from_config, aggregator_from_dict


# ---------------------------------------------------------------------------
# aggregator_from_dict
# ---------------------------------------------------------------------------

def test_none_returns_none():
    assert aggregator_from_dict(None) is None


def test_empty_dict_returns_none():
    assert aggregator_from_dict({}) is None


def test_default_strategy_is_source():
    agg = aggregator_from_dict({"flush_interval": 30})
    assert isinstance(agg, EventAggregator)
    # source strategy: key == source
    agg.record("a.log", "hello")
    agg.record("a.log", "world")
    assert agg.bucket_count() == 1


def test_source_strategy_keys_by_source():
    agg = aggregator_from_dict({"key": {"strategy": "source"}, "flush_interval": 30})
    agg.record("a.log", "x")
    agg.record("b.log", "x")
    assert agg.bucket_count() == 2


def test_pattern_strategy_keys_by_capture_group():
    cfg = {
        "key": {"strategy": "pattern", "pattern": r"(ERROR|WARN)"},
        "flush_interval": 30,
    }
    agg = aggregator_from_dict(cfg)
    agg.record("app.log", "ERROR something bad")
    agg.record("app.log", "ERROR another bad thing")
    agg.record("app.log", "WARN something mild")
    assert agg.bucket_count() == 2


def test_pattern_strategy_falls_back_to_line_when_no_match():
    cfg = {
        "key": {"strategy": "pattern", "pattern": r"(CRITICAL)"},
        "flush_interval": 30,
    }
    agg = aggregator_from_dict(cfg)
    agg.record("app.log", "INFO nothing here")
    agg.record("app.log", "INFO nothing here")
    assert agg.bucket_count() == 1  # same full line → same bucket


def test_pattern_strategy_missing_pattern_raises():
    with pytest.raises(ValueError, match="pattern"):
        aggregator_from_dict({"key": {"strategy": "pattern"}, "flush_interval": 10})


def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="Unknown"):
        aggregator_from_dict({"key": {"strategy": "hash"}, "flush_interval": 10})


def test_max_samples_passed_through():
    agg = aggregator_from_dict({"flush_interval": 30, "max_samples": 1})
    agg.record("a.log", "line1")
    agg.record("a.log", "line2")
    buckets = agg.flush()
    assert len(buckets[0].samples) == 1


def test_on_flush_callback_wired():
    cb = MagicMock()
    agg = aggregator_from_dict({"flush_interval": 30}, on_flush=cb)
    agg.record("a.log", "msg")
    agg.flush()
    cb.assert_called_once()


# ---------------------------------------------------------------------------
# aggregator_from_config
# ---------------------------------------------------------------------------

class _FakeConfig:
    def __init__(self, raw):
        self.aggregation = raw


def test_aggregator_from_config_none_attr():
    assert aggregator_from_config(_FakeConfig(None)) is None


def test_aggregator_from_config_loads_correctly():
    cfg = _FakeConfig({"flush_interval": 10, "max_samples": 2})
    agg = aggregator_from_config(cfg)
    assert isinstance(agg, EventAggregator)
