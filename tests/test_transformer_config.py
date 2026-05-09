"""Tests for logsnap.transformer_config."""
import pytest

from logsnap.transformer_config import transformer_from_dict, transformer_from_config


def test_none_returns_empty_transformer():
    t = transformer_from_dict(None)
    assert t.transform("hello") == "hello"
    assert t.rules == []


def test_empty_list_returns_empty_transformer():
    t = transformer_from_dict([])
    assert t.rules == []


def test_strip_ansi_builtin():
    t = transformer_from_dict([{"type": "strip_ansi"}])
    assert t.transform("\x1b[32mOK\x1b[0m") == "OK"


def test_uppercase_builtin():
    t = transformer_from_dict([{"type": "uppercase"}])
    assert t.transform("hello") == "HELLO"


def test_lowercase_builtin():
    t = transformer_from_dict([{"type": "lowercase"}])
    assert t.transform("HELLO") == "hello"


def test_strip_whitespace_builtin():
    t = transformer_from_dict([{"type": "strip_whitespace"}])
    assert t.transform("  hi  ") == "hi"


def test_regex_replace_rule():
    t = transformer_from_dict([{"type": "regex_replace", "pattern": r"\d+", "replacement": "X"}])
    assert t.transform("line 99") == "line X"


def test_regex_replace_custom_name():
    t = transformer_from_dict([
        {"type": "regex_replace", "pattern": "foo", "replacement": "bar", "name": "my_rule"}
    ])
    assert t.rules[0].name == "my_rule"


def test_chained_rules_applied_in_order():
    t = transformer_from_dict([
        {"type": "strip_whitespace"},
        {"type": "uppercase"},
    ])
    assert t.transform("  hello  ") == "HELLO"


def test_unknown_type_raises():
    with pytest.raises(ValueError, match="Unknown transform type"):
        transformer_from_dict([{"type": "nonexistent"}])


def test_transformer_from_config_uses_transforms_key():
    class FakeConfig:
        def to_dict(self):
            return {"transforms": [{"type": "uppercase"}]}

    t = transformer_from_config(FakeConfig())
    assert t.transform("hello") == "HELLO"


def test_transformer_from_config_missing_key_returns_empty():
    class FakeConfig:
        def to_dict(self):
            return {}

    t = transformer_from_config(FakeConfig())
    assert t.rules == []
