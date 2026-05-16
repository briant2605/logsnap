"""Tests for logsnap.dispatcher."""
from __future__ import annotations

from logsnap.aggregator import LogEvent
from logsnap.dispatcher import EventDispatcher


def _event(line: str = "hello", source: str = "app.log") -> LogEvent:
    return LogEvent(source=source, line=line, tags={})


# ---------------------------------------------------------------------------
# Sink management
# ---------------------------------------------------------------------------

def test_add_and_list_sinks():
    d = EventDispatcher()
    d.add_sink("a", lambda e: None)
    d.add_sink("b", lambda e: None)
    assert sorted(d.sink_names()) == ["a", "b"]


def test_add_non_callable_raises():
    d = EventDispatcher()
    try:
        d.add_sink("bad", "not-a-function")  # type: ignore[arg-type]
        assert False, "expected TypeError"
    except TypeError:
        pass


def test_remove_existing_sink_returns_true():
    d = EventDispatcher()
    d.add_sink("x", lambda e: None)
    assert d.remove_sink("x") is True
    assert "x" not in d.sink_names()


def test_remove_missing_sink_returns_false():
    d = EventDispatcher()
    assert d.remove_sink("ghost") is False


# ---------------------------------------------------------------------------
# Dispatch behaviour
# ---------------------------------------------------------------------------

def test_dispatch_calls_all_sinks():
    received: dict[str, list] = {"a": [], "b": []}
    d = EventDispatcher()
    d.add_sink("a", lambda e: received["a"].append(e))
    d.add_sink("b", lambda e: received["b"].append(e))

    ev = _event()
    d.dispatch(ev)

    assert received["a"] == [ev]
    assert received["b"] == [ev]


def test_dispatch_with_no_sinks_increments_dropped():
    d = EventDispatcher()
    d.dispatch(_event())
    assert d.stats.dropped == 1
    assert d.stats.dispatched == 0


def test_dispatched_counter_increments():
    d = EventDispatcher()
    d.add_sink("s", lambda e: None)
    d.dispatch(_event())
    d.dispatch(_event())
    assert d.stats.dispatched == 2


def test_sink_error_does_not_stop_other_sinks():
    received: list = []

    def bad_sink(e: LogEvent) -> None:
        raise RuntimeError("boom")

    d = EventDispatcher()
    d.add_sink("bad", bad_sink)
    d.add_sink("good", lambda e: received.append(e))

    d.dispatch(_event())

    assert len(received) == 1
    assert d.stats.sink_errors == 1


def test_error_handler_called_on_sink_failure():
    errors: list = []
    d = EventDispatcher(error_handler=lambda name, exc: errors.append((name, exc)))
    d.add_sink("boom", lambda e: (_ for _ in ()).throw(ValueError("oops")))
    d.dispatch(_event())
    assert len(errors) == 1
    assert errors[0][0] == "boom"
    assert isinstance(errors[0][1], ValueError)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def test_stats_to_dict_keys():
    d = EventDispatcher()
    keys = d.stats.to_dict().keys()
    assert set(keys) == {"dispatched", "dropped", "sink_errors"}


def test_reset_stats_clears_counters():
    d = EventDispatcher()
    d.add_sink("s", lambda e: None)
    d.dispatch(_event())
    assert d.stats.dispatched == 1
    d.reset_stats()
    assert d.stats.dispatched == 0
    assert d.stats.dropped == 0
    assert d.stats.sink_errors == 0
