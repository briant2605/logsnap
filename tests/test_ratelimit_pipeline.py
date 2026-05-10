"""Tests for RateLimitedPipeline."""

from __future__ import annotations

import time
from typing import List

import pytest

from logsnap.aggregator import LogEvent
from logsnap.ratelimit_pipeline import RateLimitedPipeline
from logsnap.throttle import ThrottleManager
from logsnap.metrics import MetricsCollector


def _event(source: str = "app.log", line: str = "hello") -> LogEvent:
    return LogEvent(source=source, line=line, tags={})


def _make_pipeline(
    rate: float = 0.0,
    burst: int = 0,
    metrics: MetricsCollector | None = None,
    maxsize: int = 100,
) -> tuple[RateLimitedPipeline, list[LogEvent]]:
    collected: list[LogEvent] = []
    throttle = ThrottleManager(default_rate=rate, default_burst=burst)
    pipeline = RateLimitedPipeline(
        handler=collected.append,
        throttle=throttle,
        metrics=metrics,
        maxsize=maxsize,
    )
    return pipeline, collected


def _drain(pipeline: RateLimitedPipeline, collected: list, timeout: float = 1.0) -> None:
    pipeline.stop()
    pipeline.join(timeout=timeout)


def test_no_rate_limit_passes_all_events():
    pipeline, collected = _make_pipeline(rate=0.0, burst=0)
    pipeline.start()
    for i in range(5):
        pipeline.put(_event(line=f"line {i}"))
    _drain(pipeline, collected)
    assert len(collected) == 5


def test_rate_limit_drops_excess_events():
    # burst=2 means only 2 tokens available immediately
    pipeline, collected = _make_pipeline(rate=1.0, burst=2)
    pipeline.start()
    for i in range(6):
        pipeline.put(_event(line=f"line {i}"))
    _drain(pipeline, collected)
    assert len(collected) == 2
    assert pipeline.dropped >= 4


def test_dropped_counter_increments_on_rate_limit():
    pipeline, collected = _make_pipeline(rate=1.0, burst=1)
    pipeline.start()
    for _ in range(4):
        pipeline.put(_event())
    _drain(pipeline, collected)
    assert pipeline.dropped >= 3


def test_metrics_recorded_for_allowed_events():
    metrics = MetricsCollector()
    pipeline, collected = _make_pipeline(rate=0.0, burst=0, metrics=metrics)
    pipeline.start()
    pipeline.put(_event(source="app.log"))
    pipeline.put(_event(source="app.log"))
    _drain(pipeline, collected)
    stats = metrics.get("app.log")
    assert stats.total_lines == 2
    assert stats.matched_lines == 2


def test_metrics_recorded_for_dropped_events():
    metrics = MetricsCollector()
    pipeline, collected = _make_pipeline(rate=1.0, burst=1, metrics=metrics)
    pipeline.start()
    for _ in range(3):
        pipeline.put(_event(source="svc.log"))
    _drain(pipeline, collected)
    stats = metrics.get("svc.log")
    assert stats.total_lines == 3
    assert stats.matched_lines == 1


def test_queue_full_increments_dropped():
    pipeline, collected = _make_pipeline(rate=0.0, burst=0, maxsize=2)
    # Do NOT start the pipeline so queue fills up
    for _ in range(5):
        pipeline.put(_event())
    assert pipeline.dropped >= 3
