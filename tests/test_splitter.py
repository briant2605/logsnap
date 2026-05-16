"""Tests for logsnap.splitter and logsnap.splitter_config."""
from __future__ import annotations

import queue
import time
from types import SimpleNamespace

import pytest

from logsnap.aggregator import LogEvent
from logsnap.splitter import EventSplitter, SplitterStats
from logsnap.splitter_config import splitter_from_config, splitter_from_dict


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _event(line: str = "hello", source: str = "app.log") -> LogEvent:
    return LogEvent(source=source, line=line, tags={})


def _make_splitter(**kwargs) -> EventSplitter:
    sp = EventSplitter(**kwargs)
    sp.start()
    return sp


def _drain(q: queue.Queue, count: int, timeout: float = 1.0):
    items = []
    deadline = time.monotonic() + timeout
    while len(items) < count and time.monotonic() < deadline:
        try:
            items.append(q.get(timeout=0.05))
        except queue.Empty:
            pass
    return items


# ---------------------------------------------------------------------------
# SplitterStats
# ---------------------------------------------------------------------------

def test_stats_defaults():
    s = SplitterStats()
    assert s.forwarded == 0
    assert s.dropped == 0


def test_stats_to_dict():
    s = SplitterStats(forwarded=3, dropped=1)
    assert s.to_dict() == {"forwarded": 3, "dropped": 1}


# ---------------------------------------------------------------------------
# EventSplitter
# ---------------------------------------------------------------------------

def test_negative_maxsize_raises():
    with pytest.raises(ValueError):
        EventSplitter(maxsize=-1)


def test_single_sink_receives_event():
    sp = _make_splitter()
    sink: queue.Queue = queue.Queue()
    sp.add_sink(sink)
    ev = _event()
    sp.put(ev)
    received = _drain(sink, 1)
    sp.stop(); sp.join(timeout=1.0)
    assert received == [ev]
    assert sp.stats.forwarded == 1
    assert sp.stats.dropped == 0


def test_multiple_sinks_all_receive_event():
    sp = _make_splitter()
    sinks = [queue.Queue() for _ in range(3)]
    for s in sinks:
        sp.add_sink(s)
    ev = _event("broadcast")
    sp.put(ev)
    for s in sinks:
        received = _drain(s, 1)
        assert received == [ev]
    sp.stop(); sp.join(timeout=1.0)
    assert sp.stats.forwarded == 3


def test_full_sink_counts_as_dropped():
    sp = _make_splitter()
    full_sink: queue.Queue = queue.Queue(maxsize=1)
    full_sink.put(_event("blocker"))  # fill it up
    sp.add_sink(full_sink)
    sp.put(_event("overflow"))
    time.sleep(0.15)
    sp.stop(); sp.join(timeout=1.0)
    assert sp.stats.dropped >= 1


def test_no_sinks_does_not_crash():
    sp = _make_splitter()
    sp.put(_event())
    time.sleep(0.1)
    sp.stop(); sp.join(timeout=1.0)
    # no assertion needed — absence of exception is the test


# ---------------------------------------------------------------------------
# splitter_from_dict / splitter_from_config
# ---------------------------------------------------------------------------

def test_none_config_returns_none():
    assert splitter_from_dict(None) is None


def test_empty_dict_returns_none():
    assert splitter_from_dict({}) is None


def test_dict_with_maxsize_creates_splitter():
    sp = splitter_from_dict({"maxsize": 512})
    assert isinstance(sp, EventSplitter)


def test_config_object_creates_splitter():
    cfg = SimpleNamespace(to_dict=lambda: {"splitter": {"maxsize": 100}})
    sp = splitter_from_config(cfg)
    assert isinstance(sp, EventSplitter)


def test_config_without_splitter_key_returns_none():
    cfg = SimpleNamespace(to_dict=lambda: {})
    assert splitter_from_config(cfg) is None
