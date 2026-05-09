"""Tests for logsnap.transformer."""
import pytest

from logsnap.transformer import (
    LineTransformer,
    TransformRule,
    lowercase_rule,
    regex_replace_rule,
    strip_ansi_rule,
    strip_whitespace_rule,
    uppercase_rule,
)


def test_transform_rule_apply():
    rule = TransformRule(name="shout", _fn=str.upper)
    assert rule.apply("hello") == "HELLO"


def test_empty_transformer_returns_line_unchanged():
    t = LineTransformer()
    assert t.transform("hello world") == "hello world"


def test_transformer_applies_single_rule():
    t = LineTransformer(rules=[uppercase_rule()])
    assert t.transform("hello") == "HELLO"


def test_transformer_chains_rules_in_order():
    t = LineTransformer(rules=[strip_whitespace_rule(), uppercase_rule()])
    assert t.transform("  hello  ") == "HELLO"


def test_transformer_add_rule_appends():
    t = LineTransformer()
    t.add_rule(lowercase_rule())
    assert t.transform("WORLD") == "world"


def test_strip_ansi_removes_escape_sequences():
    rule = strip_ansi_rule()
    line = "\x1b[31mERROR\x1b[0m: something bad"
    assert rule.apply(line) == "ERROR: something bad"


def test_strip_ansi_no_sequences_unchanged():
    rule = strip_ansi_rule()
    assert rule.apply("plain line") == "plain line"


def test_uppercase_rule():
    assert uppercase_rule().apply("abc") == "ABC"


def test_lowercase_rule():
    assert lowercase_rule().apply("ABC") == "abc"


def test_strip_whitespace_rule():
    assert strip_whitespace_rule().apply("  hi  ") == "hi"


def test_regex_replace_rule_substitutes():
    rule = regex_replace_rule(r"\d+", "NUM")
    assert rule.apply("error 42 on line 7") == "error NUM on line NUM"


def test_regex_replace_rule_no_match_unchanged():
    rule = regex_replace_rule(r"\d+", "NUM")
    assert rule.apply("no digits here") == "no digits here"


def test_regex_replace_custom_name():
    rule = regex_replace_rule(r"foo", "bar", name="foo_to_bar")
    assert rule.name == "foo_to_bar"


def test_transformer_rules_property_is_copy():
    t = LineTransformer(rules=[uppercase_rule()])
    rules = t.rules
    rules.clear()
    assert len(t.rules) == 1
