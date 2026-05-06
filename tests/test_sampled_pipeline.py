"""Tests for logsnap.sampled_pipeline.SampledPipeline."""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest

from logsnap.aggregator import LogEvent
from logsnap.sampling import LineSampler
from logsnap.sampled_pipeline import SampledPipeline


def _make_event(source: str = "app", line: str = "hello") -> LogEvent:
    return LogEvent(source=source, line=line)


def _make_sampled_pipeline(rate: int = 1):
    inner = MagicMock()
    sampler = LineSampler(rate=rate)
    return SampledPipeline(pipeline=inner, sampler=sampler), inner


# ---------------------------------------------------------------------------

def test_process_event_forwarded_when_rate_1():
    sp, inner = _make_sampled_pipeline(rate=1)
    event = _make_event()
    result = sp.process_event(event)
    assert result is True
    inner._process_event.assert_called_once_with(event)


def test_process_event_dropped_by_sampler():
    sp, inner = _make_sampled_pipeline(rate=3)
    event = _make_event()
    sp.process_event(event)          # emitted
    result2 = sp.process_event(event)  # dropped
    assert result2 is False
    assert inner._process_event.call_count == 1


def test_every_nth_event_forwarded():
    sp, inner = _make_sampled_pipeline(rate=4)
    results = [sp.process_event(_make_event()) for _ in range(8)]
    assert results.count(True) == 2
    assert inner._process_event.call_count == 2


def test_sources_sampled_independently():
    sp, inner = _make_sampled_pipeline(rate=2)
    sp.process_event(_make_event(source="a"))  # emit
    sp.process_event(_make_event(source="b"))  # emit (different source)
    sp.process_event(_make_event(source="a"))  # drop
    sp.process_event(_make_event(source="b"))  # drop
    assert inner._process_event.call_count == 2


def test_start_stop_delegated():
    sp, inner = _make_sampled_pipeline()
    sp.start()
    inner.start.assert_called_once()
    sp.stop()
    inner.stop.assert_called_once()


def test_join_delegated():
    sp, inner = _make_sampled_pipeline()
    sp.join(timeout=1.0)
    inner.join.assert_called_once_with(1.0)


def test_sampler_property():
    sp, _ = _make_sampled_pipeline(rate=5)
    assert isinstance(sp.sampler, LineSampler)
    assert sp.sampler.rate == 5


def test_pipeline_property():
    sp, inner = _make_sampled_pipeline()
    assert sp.pipeline is inner
