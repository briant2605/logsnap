"""Tests for logsnap.correlator."""
from __future__ import annotations

import time
from typing import List

import pytest

from logsnap.aggregator import LogEvent
from logsnap.correlator import CorrelationGroup, EventCorrelator


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _event(line: str, source: str = "app.log") -> LogEvent:
    return LogEvent(source=source, line=line)


def _correlator(
    pattern: str = r"req=(\w+)",
    window: float = 5.0,
    max_size: int = 100,
    mono=None,
) -> tuple[EventCorrelator, List[CorrelationGroup]]:
    flushed: List[CorrelationGroup] = []
    kwargs = dict(pattern=pattern, on_flush=flushed.append, window_seconds=window, max_size=max_size)
    if mono is not None:
        kwargs["_mono"] = mono
    return EventCorrelator(**kwargs), flushed


# ---------------------------------------------------------------------------
# CorrelationGroup
# ---------------------------------------------------------------------------

def test_group_add_increments_events():
    g = CorrelationGroup(key="abc")
    g.add(_event("hello"))
    assert len(g.events) == 1


def test_group_to_dict_keys():
    g = CorrelationGroup(key="x")
    g.add(_event("line", source="s1"))
    d = g.to_dict()
    assert d["key"] == "x"
    assert d["count"] == 1
    assert "s1" in d["sources"]


# ---------------------------------------------------------------------------
# EventCorrelator – basic grouping
# ---------------------------------------------------------------------------

def test_events_with_same_key_grouped():
    c, flushed = _correlator()
    c.record(_event("req=abc start"))
    c.record(_event("req=abc end"))
    c.flush_all()
    assert len(flushed) == 1
    assert flushed[0].key == "abc"
    assert len(flushed[0].events) == 2


def test_events_with_different_keys_make_separate_groups():
    c, flushed = _correlator()
    c.record(_event("req=aaa line"))
    c.record(_event("req=bbb line"))
    c.flush_all()
    keys = {g.key for g in flushed}
    assert keys == {"aaa", "bbb"}


def test_non_matching_event_ignored():
    c, flushed = _correlator()
    c.record(_event("no match here"))
    c.flush_all()
    assert flushed == []


# ---------------------------------------------------------------------------
# max_size flush
# ---------------------------------------------------------------------------

def test_max_size_triggers_flush():
    c, flushed = _correlator(max_size=3)
    for i in range(3):
        c.record(_event(f"req=X event {i}"))
    assert len(flushed) == 1
    assert len(flushed[0].events) == 3


def test_after_max_size_flush_new_group_starts():
    c, flushed = _correlator(max_size=2)
    for i in range(4):
        c.record(_event(f"req=X event {i}"))
    assert len(flushed) == 2


# ---------------------------------------------------------------------------
# window expiry
# ---------------------------------------------------------------------------

def test_window_expiry_flushes_group():
    tick = [0.0]

    def mono():
        return tick[0]

    c, flushed = _correlator(window=2.0, mono=mono)
    c.record(_event("req=Z start"))
    tick[0] = 3.0  # advance past window
    c.record(_event("req=Z end"))  # triggers _expire_old before adding
    assert len(flushed) == 1
    assert flushed[0].key == "Z"


# ---------------------------------------------------------------------------
# flush_all
# ---------------------------------------------------------------------------

def test_flush_all_clears_groups():
    c, flushed = _correlator()
    c.record(_event("req=A"))
    c.record(_event("req=B"))
    c.flush_all()
    assert len(flushed) == 2
    # second flush_all should produce nothing
    c.flush_all()
    assert len(flushed) == 2


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------

def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        EventCorrelator(pattern=r"x", on_flush=lambda g: None, window_seconds=0)


def test_invalid_max_size_raises():
    with pytest.raises(ValueError, match="max_size"):
        EventCorrelator(pattern=r"x", on_flush=lambda g: None, max_size=0)
