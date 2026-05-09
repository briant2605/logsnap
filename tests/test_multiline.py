"""Tests for MultilineAssembler and MultilineConfig."""
from __future__ import annotations

from typing import List

import pytest

from logsnap.multiline import MultilineAssembler, MultilineConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assembler(pattern: str = r"^\S", max_lines: int = 500, timeout: float = 5.0):
    """Return (assembler, emitted_list) pair."""
    emitted: List[str] = []
    cfg = MultilineConfig(start_pattern=pattern, max_lines=max_lines, flush_timeout=timeout)
    asm = MultilineAssembler(cfg, emitted.append)
    return asm, emitted


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_single_line_event_emitted_on_next_start():
    asm, emitted = _assembler()
    asm.feed("INFO start")
    assert emitted == []  # not yet flushed
    asm.feed("INFO second")  # new start triggers flush of first
    assert emitted == ["INFO start"]


def test_continuation_lines_joined():
    asm, emitted = _assembler()
    asm.feed("ERROR boom")
    asm.feed("  at line 1")
    asm.feed("  at line 2")
    asm.feed("INFO next")  # triggers flush
    assert len(emitted) == 1
    assert emitted[0] == "ERROR boom\n  at line 1\n  at line 2"


def test_explicit_flush_emits_pending():
    asm, emitted = _assembler()
    asm.feed("WARN something")
    asm.feed("  detail")
    asm.flush()
    assert emitted == ["WARN something\n  detail"]


def test_max_lines_triggers_flush():
    asm, emitted = _assembler(max_lines=3)
    # Feed 3 continuation lines (no new start)
    asm.feed("ERROR root")
    asm.feed("  line1")
    asm.feed("  line2")
    # 4th line exceeds max → flushes previous buffer first
    asm.feed("  line3")
    assert len(emitted) == 1
    assert "ERROR root" in emitted[0]


def test_flush_if_stale_respects_timeout():
    ticks = [0.0]

    def clock():
        return ticks[0]

    emitted: list = []
    cfg = MultilineConfig(flush_timeout=1.0)
    asm = MultilineAssembler(cfg, emitted.append, clock=clock)

    asm.feed("INFO waiting")
    ticks[0] = 0.5
    asm.flush_if_stale()  # not yet stale
    assert emitted == []

    ticks[0] = 1.5
    asm.flush_if_stale()  # now stale
    assert emitted == ["INFO waiting"]


def test_flush_if_stale_no_buffer_is_noop():
    asm, emitted = _assembler()
    asm.flush_if_stale()  # empty buffer — should not raise
    assert emitted == []


def test_custom_start_pattern():
    # Lines starting with a timestamp are new events
    asm, emitted = _assembler(pattern=r"^\d{4}-")
    asm.feed("2024-01-01 ERROR first")
    asm.feed("  stacktrace")
    asm.feed("2024-01-01 INFO second")
    assert emitted == ["2024-01-01 ERROR first\n  stacktrace"]
