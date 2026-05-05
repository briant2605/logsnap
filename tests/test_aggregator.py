"""Tests for LogAggregator."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from logsnap.aggregator import LogAggregator, LogEvent
from logsnap.filter import LineFilter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_lines(path: Path, lines: list[str], delay: float = 0.05) -> None:
    """Append lines to *path* with a small delay so the tailer can pick them up."""
    time.sleep(delay)
    with path.open("a") as fh:
        for line in lines:
            fh.write(line + "\n")
            fh.flush()


def _collect(
    aggregator: LogAggregator,
    expected: int,
    timeout: float = 3.0,
) -> list[LogEvent]:
    collected: list[LogEvent] = []
    deadline = time.monotonic() + timeout
    for event in aggregator.events(timeout=0.1):
        collected.append(event)
        if len(collected) >= expected:
            break
        if time.monotonic() > deadline:
            break
    aggregator.stop()
    return collected


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_aggregator_collects_from_single_file(tmp_path: Path) -> None:
    log = tmp_path / "app.log"
    log.write_text("")

    agg = LogAggregator([log], poll_interval=0.05)
    agg.start()

    writer = threading.Thread(target=_write_lines, args=(log, ["hello", "world"]))
    writer.start()

    events = _collect(agg, expected=2)
    writer.join()

    lines = [e.line for e in events]
    assert "hello" in lines
    assert "world" in lines


def test_aggregator_tags_source_correctly(tmp_path: Path) -> None:
    log = tmp_path / "service.log"
    log.write_text("")

    agg = LogAggregator([log], poll_interval=0.05)
    agg.start()

    threading.Thread(target=_write_lines, args=(log, ["ping"])).start()
    events = _collect(agg, expected=1)

    assert events[0].source == "service.log"


def test_aggregator_applies_filter(tmp_path: Path) -> None:
    log = tmp_path / "mixed.log"
    log.write_text("")

    lf = LineFilter(include_patterns=["ERROR"])
    agg = LogAggregator([log], line_filter=lf, poll_interval=0.05)
    agg.start()

    lines = ["INFO all good", "ERROR something broke", "DEBUG trace"]
    threading.Thread(target=_write_lines, args=(log, lines)).start()

    events = _collect(agg, expected=1, timeout=2.0)
    assert all("ERROR" in e.line for e in events)


def test_aggregator_collects_from_multiple_files(tmp_path: Path) -> None:
    log_a = tmp_path / "a.log"
    log_b = tmp_path / "b.log"
    log_a.write_text("")
    log_b.write_text("")

    agg = LogAggregator([log_a, log_b], poll_interval=0.05)
    agg.start()

    threading.Thread(target=_write_lines, args=(log_a, ["from-a"])).start()
    threading.Thread(target=_write_lines, args=(log_b, ["from-b"])).start()

    events = _collect(agg, expected=2)
    sources = {e.source for e in events}
    assert "a.log" in sources
    assert "b.log" in sources
