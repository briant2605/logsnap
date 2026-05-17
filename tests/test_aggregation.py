"""Tests for logsnap.aggregation."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from logsnap.aggregation import AggregationBucket, EventAggregator


# ---------------------------------------------------------------------------
# AggregationBucket
# ---------------------------------------------------------------------------

def test_bucket_add_increments_count():
    b = AggregationBucket(key="k")
    b.add("line 1")
    b.add("line 2")
    assert b.count == 2


def test_bucket_samples_capped():
    b = AggregationBucket(key="k", max_samples=2)
    for i in range(5):
        b.add(f"line {i}")
    assert len(b.samples) == 2
    assert b.samples == ["line 0", "line 1"]


def test_bucket_to_dict_keys():
    b = AggregationBucket(key="mykey")
    b.add("hello")
    d = b.to_dict()
    assert d["key"] == "mykey"
    assert d["count"] == 1
    assert "samples" in d
    assert "first_seen" in d
    assert "last_seen" in d


def test_bucket_age_is_non_negative():
    b = AggregationBucket(key="k")
    assert b.age() >= 0


# ---------------------------------------------------------------------------
# EventAggregator
# ---------------------------------------------------------------------------

def test_aggregator_invalid_interval_raises():
    with pytest.raises(ValueError):
        EventAggregator(key_fn=lambda s, l: s, flush_interval=0)


def test_aggregator_record_creates_bucket():
    agg = EventAggregator(key_fn=lambda s, l: s, flush_interval=60)
    agg.record("app.log", "error occurred")
    assert agg.bucket_count() == 1


def test_aggregator_same_key_increments():
    agg = EventAggregator(key_fn=lambda s, l: s, flush_interval=60)
    agg.record("app.log", "line 1")
    agg.record("app.log", "line 2")
    assert agg.bucket_count() == 1


def test_aggregator_different_keys_separate_buckets():
    agg = EventAggregator(key_fn=lambda s, l: s, flush_interval=60)
    agg.record("a.log", "x")
    agg.record("b.log", "y")
    assert agg.bucket_count() == 2


def test_aggregator_flush_resets_buckets():
    agg = EventAggregator(key_fn=lambda s, l: s, flush_interval=60)
    agg.record("a.log", "msg")
    buckets = agg.flush()
    assert len(buckets) == 1
    assert agg.bucket_count() == 0


def test_aggregator_flush_calls_on_flush():
    cb = MagicMock()
    agg = EventAggregator(key_fn=lambda s, l: s, flush_interval=60, on_flush=cb)
    agg.record("a.log", "msg")
    agg.flush()
    cb.assert_called_once()
    assert len(cb.call_args[0][0]) == 1


def test_aggregator_flush_no_callback_on_empty():
    cb = MagicMock()
    agg = EventAggregator(key_fn=lambda s, l: s, flush_interval=60, on_flush=cb)
    agg.flush()  # empty
    cb.assert_not_called()


def test_aggregator_start_stop_join():
    agg = EventAggregator(key_fn=lambda s, l: s, flush_interval=100)
    agg.start()
    agg.record("x.log", "hi")
    agg.stop()
    agg.join(timeout=2.0)
    # After join the bucket should have been flushed by the thread's final flush.
    assert agg.bucket_count() == 0
