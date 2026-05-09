"""Tests for logsnap.heartbeat."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from logsnap.heartbeat import HeartbeatConfig, HeartbeatEmitter, heartbeat_from_dict


# ---------------------------------------------------------------------------
# HeartbeatConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = HeartbeatConfig()
    assert cfg.interval == 60.0
    assert "heartbeat" in cfg.message
    assert cfg.source == "__heartbeat__"


def test_config_negative_interval_raises():
    with pytest.raises(ValueError, match="interval must be positive"):
        HeartbeatConfig(interval=-1.0)


def test_config_zero_interval_raises():
    with pytest.raises(ValueError):
        HeartbeatConfig(interval=0)


# ---------------------------------------------------------------------------
# HeartbeatEmitter – unit tests with a fake clock / manual _emit
# ---------------------------------------------------------------------------

def test_emit_calls_callback_with_source_and_line():
    received: list[tuple[str, str]] = []
    cfg = HeartbeatConfig(interval=1.0, source="__hb__", message="ping")
    emitter = HeartbeatEmitter(cfg, lambda s, l: received.append((s, l)))
    emitter._emit()  # call directly without starting the thread
    assert len(received) == 1
    source, line = received[0]
    assert source == "__hb__"
    assert line.startswith("ping")
    assert "ts=" in line


def test_emit_line_contains_iso_timestamp():
    lines: list[str] = []
    cfg = HeartbeatConfig(interval=1.0)
    emitter = HeartbeatEmitter(cfg, lambda s, l: lines.append(l))
    emitter._emit()
    assert "T" in lines[0]  # ISO-8601 separator
    assert "Z" in lines[0]


# ---------------------------------------------------------------------------
# HeartbeatEmitter – integration: start / stop
# ---------------------------------------------------------------------------

def test_start_stop_no_error():
    cfg = HeartbeatConfig(interval=0.05)
    emitter = HeartbeatEmitter(cfg, lambda s, l: None)
    emitter.start()
    time.sleep(0.02)
    emitter.stop(timeout=2.0)


def test_callback_invoked_at_least_once():
    event = threading.Event()
    cfg = HeartbeatConfig(interval=0.05)
    emitter = HeartbeatEmitter(cfg, lambda s, l: event.set())
    emitter.start()
    fired = event.wait(timeout=2.0)
    emitter.stop(timeout=2.0)
    assert fired, "heartbeat callback was never invoked"


def test_start_twice_is_safe():
    cfg = HeartbeatConfig(interval=0.5)
    emitter = HeartbeatEmitter(cfg, lambda s, l: None)
    emitter.start()
    emitter.start()  # second call should be a no-op
    emitter.stop(timeout=2.0)


# ---------------------------------------------------------------------------
# heartbeat_from_dict
# ---------------------------------------------------------------------------

def test_from_dict_none_returns_none():
    assert heartbeat_from_dict(None) is None


def test_from_dict_empty_returns_none():
    assert heartbeat_from_dict({}) is None


def test_from_dict_full():
    cfg = heartbeat_from_dict({"interval": 30, "message": "alive", "source": "hb"})
    assert cfg is not None
    assert cfg.interval == 30.0
    assert cfg.message == "alive"
    assert cfg.source == "hb"


def test_from_dict_partial_uses_defaults():
    cfg = heartbeat_from_dict({"interval": 10})
    assert cfg is not None
    assert cfg.interval == 10.0
    assert cfg.source == "__heartbeat__"
