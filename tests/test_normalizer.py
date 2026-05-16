"""Tests for logsnap.normalizer."""
import pytest

from logsnap.normalizer import (
    LineNormalizer,
    NormalizeRule,
    _collapse_whitespace,
    _strip_ansi,
    _strip_whitespace,
    _to_lowercase,
    _to_uppercase,
)


# ---------------------------------------------------------------------------
# NormalizeRule
# ---------------------------------------------------------------------------

def test_normalize_rule_apply_calls_fn():
    rule = NormalizeRule(name="upper", _fn=str.upper)
    assert rule.apply("hello") == "HELLO"


def test_normalize_rule_apply_passes_result_through():
    rule = NormalizeRule(name="noop", _fn=lambda s: s)
    assert rule.apply("unchanged") == "unchanged"


# ---------------------------------------------------------------------------
# Built-in helpers
# ---------------------------------------------------------------------------

def test_strip_ansi_removes_escape_codes():
    assert _strip_ansi("\x1b[31mERROR\x1b[0m") == "ERROR"


def test_strip_ansi_no_codes_unchanged():
    assert _strip_ansi("plain line") == "plain line"


def test_strip_whitespace_trims_edges():
    assert _strip_whitespace("  hello  ") == "hello"


def test_collapse_whitespace_reduces_spaces():
    assert _collapse_whitespace("a  b\t\tc") == "a b c"


def test_to_lowercase():
    assert _to_lowercase("WARN") == "warn"


def test_to_uppercase():
    assert _to_uppercase("info") == "INFO"


# ---------------------------------------------------------------------------
# LineNormalizer
# ---------------------------------------------------------------------------

def test_empty_normalizer_returns_line_unchanged():
    n = LineNormalizer()
    assert n.normalize("hello world") == "hello world"


def test_add_rule_increases_length():
    n = LineNormalizer()
    n.add_rule(NormalizeRule(name="noop", _fn=lambda s: s))
    assert len(n) == 1


def test_single_rule_applied():
    n = LineNormalizer()
    n.add_rule(NormalizeRule(name="upper", _fn=str.upper))
    assert n.normalize("hello") == "HELLO"


def test_rules_applied_in_order():
    n = LineNormalizer()
    n.add_rule(NormalizeRule(name="strip", _fn=str.strip))
    n.add_rule(NormalizeRule(name="upper", _fn=str.upper))
    assert n.normalize("  hello  ") == "HELLO"


def test_from_names_strip_ansi():
    n = LineNormalizer.from_names(["strip_ansi"])
    assert n.normalize("\x1b[32mOK\x1b[0m") == "OK"


def test_from_names_multiple_steps():
    n = LineNormalizer.from_names(["strip_whitespace", "lowercase"])
    assert n.normalize("  HELLO  ") == "hello"


def test_from_names_unknown_raises():
    with pytest.raises(ValueError, match="Unknown normalization step"):
        LineNormalizer.from_names(["nonexistent"])


def test_from_names_empty_list_returns_noop_normalizer():
    n = LineNormalizer.from_names([])
    assert n.normalize("unchanged") == "unchanged"
    assert len(n) == 0


def test_from_names_collapse_whitespace():
    n = LineNormalizer.from_names(["collapse_whitespace"])
    assert n.normalize("a   b") == "a b"


def test_from_names_uppercase():
    n = LineNormalizer.from_names(["uppercase"])
    assert n.normalize("warn") == "WARN"
