"""Tests for output formatters."""

from __future__ import annotations

import io
import json

import pytest

from logsnap.aggregator import LogEvent
from logsnap.output import JsonFormatter, PlainFormatter


# ---------------------------------------------------------------------------
# PlainFormatter
# ---------------------------------------------------------------------------

def test_plain_format_no_color() -> None:
    fmt = PlainFormatter()
    event = LogEvent(source="app.log", line="hello world")
    assert fmt.format(event) == "[app.log] hello world"


def test_plain_format_with_color() -> None:
    fmt = PlainFormatter(colorize=True)
    event = LogEvent(source="app.log", line="hello")
    result = fmt.format(event)
    # Should contain ANSI reset sequence
    assert "\033[0m" in result
    assert "app.log" in result
    assert "hello" in result


def test_plain_emit_writes_lines() -> None:
    buf = io.StringIO()
    fmt = PlainFormatter(stream=buf)
    events = [
        LogEvent(source="a.log", line="line one"),
        LogEvent(source="b.log", line="line two"),
    ]
    fmt.emit(iter(events))
    output = buf.getvalue()
    assert "[a.log] line one" in output
    assert "[b.log] line two" in output


# ---------------------------------------------------------------------------
# JsonFormatter
# ---------------------------------------------------------------------------

def test_json_format_structure() -> None:
    fmt = JsonFormatter()
    event = LogEvent(source="svc.log", line="boom")
    parsed = json.loads(fmt.format(event))
    assert parsed == {"source": "svc.log", "line": "boom"}


def test_json_emit_writes_ndjson() -> None:
    buf = io.StringIO()
    fmt = JsonFormatter(stream=buf)
    events = [
        LogEvent(source="x.log", line="alpha"),
        LogEvent(source="y.log", line="beta"),
    ]
    fmt.emit(iter(events))
    lines = [l for l in buf.getvalue().splitlines() if l]
    assert len(lines) == 2
    assert json.loads(lines[0])["line"] == "alpha"
    assert json.loads(lines[1])["source"] == "y.log"


def test_log_event_str() -> None:
    event = LogEvent(source="demo.log", line="test message")
    assert str(event) == "[demo.log] test message"
