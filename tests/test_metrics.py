"""Tests for logsnap.metrics."""

import time
import threading

import pytest

from logsnap.metrics import MetricsCollector, SourceMetrics


def test_source_metrics_defaults():
    m = SourceMetrics()
    assert m.lines_read == 0
    assert m.lines_matched == 0
    assert m.bytes_read == 0
    assert m.rotations == 0
    assert m.last_event_ts == 0.0


def test_source_metrics_to_dict():
    m = SourceMetrics(lines_read=5, lines_matched=3, bytes_read=100, rotations=1, last_event_ts=1.0)
    d = m.to_dict()
    assert d["lines_read"] == 5
    assert d["lines_matched"] == 3
    assert d["bytes_read"] == 100
    assert d["rotations"] == 1
    assert d["last_event_ts"] == 1.0


def test_record_line_increments_counters():
    col = MetricsCollector()
    col.record_line("/var/log/app.log", "hello world", matched=True)
    snap = col.snapshot()
    src = snap["sources"]["/var/log/app.log"]
    assert src["lines_read"] == 1
    assert src["lines_matched"] == 1
    assert src["bytes_read"] == len(b"hello world")


def test_unmatched_line_not_counted_as_matched():
    col = MetricsCollector()
    col.record_line("/var/log/app.log", "debug noise", matched=False)
    src = col.snapshot()["sources"]["/var/log/app.log"]
    assert src["lines_read"] == 1
    assert src["lines_matched"] == 0


def test_record_rotation():
    col = MetricsCollector()
    col.record_rotation("/var/log/app.log")
    col.record_rotation("/var/log/app.log")
    src = col.snapshot()["sources"]["/var/log/app.log"]
    assert src["rotations"] == 2


def test_snapshot_uptime_increases():
    col = MetricsCollector()
    time.sleep(0.05)
    assert col.snapshot()["uptime_seconds"] >= 0.04


def test_reset_clears_state():
    col = MetricsCollector()
    col.record_line("/var/log/a.log", "x", matched=True)
    col.reset()
    assert col.snapshot()["sources"] == {}


def test_thread_safety():
    col = MetricsCollector()
    source = "/var/log/concurrent.log"

    def worker():
        for _ in range(200):
            col.record_line(source, "line", matched=True)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    src = col.snapshot()["sources"][source]
    assert src["lines_read"] == 1000
    assert src["lines_matched"] == 1000
