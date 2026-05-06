"""Tests for the Pipeline wiring layer."""
from __future__ import annotations

import io
import queue
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from logsnap.aggregator import LogEvent
from logsnap.filter import LineFilter
from logsnap.metrics import MetricsCollector
from logsnap.output import PlainFormatter
from logsnap.pipeline import Pipeline
from logsnap.throttle import ThrottleManager


def _make_pipeline(events, line_filter=None, throttle=None, stream=None):
    """Build a Pipeline backed by a fake aggregator that yields `events`."""
    agg = MagicMock()
    stop_holder = {}

    def fake_events(stop_event):
        stop_holder["ev"] = stop_event
        yield from events

    agg.events.side_effect = fake_events
    agg.start = MagicMock()
    agg.stop = MagicMock()

    buf = stream or io.StringIO()
    p = Pipeline(
        aggregator=agg,
        line_filter=line_filter,
        throttle=throttle,
        metrics=MetricsCollector(),
        formatter=PlainFormatter(use_color=False),
        output_stream=buf,
    )
    return p, buf


def _drain(pipeline, buf, timeout=2.0):
    pipeline.start()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(0.05)
        if pipeline._thread and not pipeline._thread.is_alive():
            break
    pipeline.stop()
    return buf.getvalue()


# ---------------------------------------------------------------------------

def test_pipeline_emits_matching_lines():
    events = [
        LogEvent(source="app.log", line="ERROR something bad"),
        LogEvent(source="app.log", line="INFO all good"),
    ]
    filt = LineFilter(include=["ERROR"])
    p, buf = _make_pipeline(events, line_filter=filt)
    out = _drain(p, buf)
    assert "ERROR something bad" in out
    assert "INFO all good" not in out


def test_pipeline_records_metrics_for_unmatched():
    events = [LogEvent(source="app.log", line="DEBUG noise")]
    filt = LineFilter(include=["ERROR"])
    p, buf = _make_pipeline(events, line_filter=filt)
    _drain(p, buf)
    sm = p.metrics.get("app.log")
    assert sm.total_lines == 1
    assert sm.matched_lines == 0


def test_pipeline_throttle_suppresses_excess(monkeypatch):
    """When ThrottleManager.allow returns False the line must not be emitted."""
    events = [LogEvent(source="s", line="hi")]
    throttle = MagicMock()
    throttle.allow.return_value = False
    p, buf = _make_pipeline(events, throttle=throttle)
    _drain(p, buf)
    assert buf.getvalue() == ""


def test_pipeline_start_calls_aggregator_start():
    p, _ = _make_pipeline([])
    p.start()
    p._aggregator.start.assert_called_once()
    p.stop()


def test_pipeline_stop_calls_aggregator_stop():
    p, _ = _make_pipeline([])
    p.start()
    p.stop()
    p._aggregator.stop.assert_called_once()
