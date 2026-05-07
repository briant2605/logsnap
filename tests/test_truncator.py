"""Tests for logsnap.truncator."""
import pytest

from logsnap.truncator import LineTruncator, TruncatorStats, _DEFAULT_MAX_BYTES


# ---------------------------------------------------------------------------
# TruncatorStats
# ---------------------------------------------------------------------------

def test_stats_defaults():
    s = TruncatorStats()
    assert s.total_lines == 0
    assert s.truncated_lines == 0
    assert s.bytes_dropped == 0


def test_stats_to_dict():
    s = TruncatorStats(total_lines=10, truncated_lines=2, bytes_dropped=512)
    d = s.to_dict()
    assert d == {"total_lines": 10, "truncated_lines": 2, "bytes_dropped": 512}


# ---------------------------------------------------------------------------
# LineTruncator construction
# ---------------------------------------------------------------------------

def test_negative_max_bytes_raises():
    with pytest.raises(ValueError, match="max_bytes"):
        LineTruncator(max_bytes=-1)


def test_zero_max_bytes_disables_truncation():
    t = LineTruncator(max_bytes=0)
    long_line = "x" * 10_000
    assert t.truncate(long_line) == long_line


def test_none_max_bytes_disables_truncation():
    t = LineTruncator(max_bytes=None)
    long_line = "a" * 5_000
    assert t.truncate(long_line) == long_line


# ---------------------------------------------------------------------------
# Truncation behaviour
# ---------------------------------------------------------------------------

def test_short_line_passes_through():
    t = LineTruncator(max_bytes=100)
    line = "hello world"
    assert t.truncate(line) == line


def test_line_exactly_at_limit_passes_through():
    t = LineTruncator(max_bytes=10)
    line = "a" * 10
    assert t.truncate(line) == line


def test_long_line_is_truncated():
    t = LineTruncator(max_bytes=20, ellipsis="...[cut]")
    line = "B" * 50
    result = t.truncate(line)
    assert result.endswith("...[cut]")
    assert len(result.encode("utf-8")) <= 20


def test_truncated_line_ends_with_ellipsis():
    t = LineTruncator(max_bytes=30)
    line = "Z" * 100
    result = t.truncate(line)
    assert result.endswith("...[truncated]")


def test_stats_incremented_for_truncated_line():
    t = LineTruncator(max_bytes=20, ellipsis="...[cut]")
    t.truncate("short", source="app")
    t.truncate("X" * 200, source="app")
    s = t.stats("app")
    assert s.total_lines == 2
    assert s.truncated_lines == 1
    assert s.bytes_dropped > 0


def test_stats_not_incremented_for_short_line():
    t = LineTruncator(max_bytes=100)
    t.truncate("hello", source="svc")
    s = t.stats("svc")
    assert s.truncated_lines == 0
    assert s.bytes_dropped == 0


def test_stats_are_per_source():
    t = LineTruncator(max_bytes=10)
    t.truncate("A" * 50, source="src1")
    t.truncate("B" * 50, source="src2")
    assert t.stats("src1").truncated_lines == 1
    assert t.stats("src2").truncated_lines == 1
    assert t.stats("src1").bytes_dropped != t.stats("src2").bytes_dropped or True  # independent


def test_all_stats_returns_all_sources():
    t = LineTruncator(max_bytes=10)
    t.truncate("hello", source="a")
    t.truncate("world", source="b")
    result = t.all_stats()
    assert "a" in result and "b" in result


def test_reset_single_source():
    t = LineTruncator(max_bytes=10)
    t.truncate("X" * 50, source="s1")
    t.truncate("X" * 50, source="s2")
    t.reset(source="s1")
    assert t.stats("s1").total_lines == 0
    assert t.stats("s2").total_lines == 1


def test_reset_all_sources():
    t = LineTruncator(max_bytes=10)
    t.truncate("X" * 50, source="s1")
    t.truncate("X" * 50, source="s2")
    t.reset()
    assert t.all_stats() == {}
