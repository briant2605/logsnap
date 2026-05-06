"""Tests for logsnap.dedup.DedupFilter."""

import pytest
from logsnap.dedup import DedupFilter


def _clock(values):
    """Return a callable that yields successive values from *values*."""
    it = iter(values)

    def _mono():
        return next(it)

    return _mono


def test_first_occurrence_is_not_duplicate():
    df = DedupFilter(window=5.0, _mono=_clock([0.0]))
    assert df.is_duplicate("hello") is False


def test_same_line_within_window_is_duplicate():
    df = DedupFilter(window=5.0, _mono=_clock([0.0, 3.0]))
    df.is_duplicate("hello")
    assert df.is_duplicate("hello") is True


def test_same_line_after_window_is_not_duplicate():
    df = DedupFilter(window=5.0, _mono=_clock([0.0, 6.0]))
    df.is_duplicate("hello")
    assert df.is_duplicate("hello") is False


def test_different_lines_are_independent():
    df = DedupFilter(window=5.0, _mono=_clock([0.0, 0.1, 0.2, 0.3]))
    df.is_duplicate("line A")
    df.is_duplicate("line B")
    assert df.is_duplicate("line A") is True
    assert df.is_duplicate("line B") is True


def test_reset_clears_history():
    df = DedupFilter(window=5.0, _mono=_clock([0.0, 1.0, 2.0]))
    df.is_duplicate("hello")
    df.reset()
    assert df.is_duplicate("hello") is False


def test_max_entries_evicts_oldest():
    times = iter(range(200))
    df = DedupFilter(window=9999.0, max_entries=3, _mono=lambda: next(times))
    for line in ["a", "b", "c"]:
        df.is_duplicate(line)
    # Adding a 4th entry should evict "a"
    df.is_duplicate("d")
    # "a" is gone — next call should be treated as new (not duplicate)
    assert df.is_duplicate("a") is False


def test_negative_window_raises():
    with pytest.raises(ValueError):
        DedupFilter(window=-1.0)


def test_window_zero_never_deduplicates():
    """A window of 0 means every line is immediately expired."""
    df = DedupFilter(window=0.0, _mono=_clock([0.0, 0.0]))
    df.is_duplicate("msg")
    # Second call at same timestamp: 0.0 - 0.0 = 0.0, NOT < 0 → new
    assert df.is_duplicate("msg") is False
