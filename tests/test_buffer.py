"""Tests for logsnap.buffer.EventBuffer."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from logsnap.aggregator import LogEvent
from logsnap.buffer import BufferStats, EventBuffer


def _event(line: str = "hello", source: str = "app.log") -> LogEvent:
    return LogEvent(source=source, line=line)


# ---------------------------------------------------------------------------
def test_invalid_maxsize_raises():
    with pytest.raises(ValueError):
        EventBuffer(maxsize=0)


def test_put_and_drain_single_event():
    buf = EventBuffer(maxsize=10)
    buf.put(_event("first"))
    items = buf.drain()
    assert len(items) == 1
    assert items[0].line == "first"


def test_drain_empties_buffer():
    buf = EventBuffer(maxsize=10)
    for i in range(5):
        buf.put(_event(str(i)))
    buf.drain()
    assert len(buf) == 0


def test_drain_max_items_partial():
    buf = EventBuffer(maxsize=10)
    for i in range(6):
        buf.put(_event(str(i)))
    items = buf.drain(max_items=3)
    assert len(items) == 3
    assert len(buf) == 3


def test_overflow_drops_oldest():
    buf = EventBuffer(maxsize=3)
    for i in range(5):
        buf.put(_event(str(i)))
    items = buf.drain()
    lines = [e.line for e in items]
    assert lines == ["2", "3", "4"]


def test_on_drop_callback_called():
    dropped = []
    buf = EventBuffer(maxsize=2, on_drop=dropped.append)
    buf.put(_event("a"))
    buf.put(_event("b"))
    buf.put(_event("c"))  # should drop "a"
    assert len(dropped) == 1
    assert dropped[0].line == "a"


def test_put_returns_false_on_drop():
    buf = EventBuffer(maxsize=1)
    buf.put(_event("first"))
    result = buf.put(_event("second"))
    assert result is False


def test_put_returns_true_when_not_full():
    buf = EventBuffer(maxsize=5)
    result = buf.put(_event("ok"))
    assert result is True


def test_stats_track_enqueued_and_dropped():
    buf = EventBuffer(maxsize=2)
    buf.put(_event("a"))
    buf.put(_event("b"))
    buf.put(_event("c"))  # drop "a"
    s = buf.stats
    assert s.total_enqueued == 3
    assert s.total_dropped == 1
    assert s.current_size == 2


def test_stats_to_dict_keys():
    s = BufferStats(total_enqueued=10, total_dropped=2, current_size=8)
    d = s.to_dict()
    assert set(d.keys()) == {"total_enqueued", "total_dropped", "current_size"}


def test_peek_does_not_remove_events():
    buf = EventBuffer(maxsize=5)
    buf.put(_event("x"))
    snapshot = buf.peek()
    assert len(snapshot) == 1
    assert len(buf) == 1


def test_thread_safety_concurrent_puts():
    buf = EventBuffer(maxsize=500)
    errors: list = []

    def _producer():
        try:
            for i in range(100):
                buf.put(_event(str(i)))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_producer) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert buf.stats.total_enqueued == 500
