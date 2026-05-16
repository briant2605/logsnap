"""Tests for logsnap.masker and logsnap.masker_config."""
import re
import types

import pytest

from logsnap.masker import MaskRule, Masker
from logsnap.masker_config import masker_from_dict, masker_from_config


# ---------------------------------------------------------------------------
# MaskRule
# ---------------------------------------------------------------------------

def test_mask_rule_replaces_named_group():
    rule = MaskRule(re.compile(r"password=(?P<value>\S+)"), mask="[REDACTED]")
    result = rule.apply("password=s3cr3t other=data")
    assert result == "password=[REDACTED] other=data"


def test_mask_rule_replaces_all_occurrences():
    rule = MaskRule(re.compile(r"token=(?P<value>\w+)"), mask="***")
    result = rule.apply("token=abc token=xyz")
    assert "abc" not in result
    assert "xyz" not in result
    assert result.count("***") == 2


def test_mask_rule_no_match_returns_original():
    rule = MaskRule(re.compile(r"secret=(?P<value>\S+)"))
    line = "nothing sensitive here"
    assert rule.apply(line) == line


def test_mask_rule_repr_uses_label():
    rule = MaskRule(re.compile(r"x"), label="my_rule")
    assert "my_rule" in repr(rule)


def test_mask_rule_repr_falls_back_to_pattern():
    rule = MaskRule(re.compile(r"(?P<value>\d+)"))
    assert "(?P<value>" in repr(rule)


# ---------------------------------------------------------------------------
# Masker
# ---------------------------------------------------------------------------

def test_masker_empty_returns_line_unchanged():
    masker = Masker()
    assert masker.apply("hello world") == "hello world"


def test_masker_applies_single_rule():
    rule = MaskRule(re.compile(r"(?P<value>\b\d{4}\b)"), mask="XXXX")
    masker = Masker([rule])
    assert masker.apply("code 1234 end") == "code XXXX end"


def test_masker_chains_rules_in_order():
    r1 = MaskRule(re.compile(r"(?P<value>foo)"), mask="AAA")
    r2 = MaskRule(re.compile(r"(?P<value>bar)"), mask="BBB")
    masker = Masker([r1, r2])
    assert masker.apply("foo bar") == "AAA BBB"


def test_masker_stats_lists_rules():
    r1 = MaskRule(re.compile(r"x"), label="rule1")
    masker = Masker([r1])
    s = masker.stats()
    assert "rules" in s
    assert len(s["rules"]) == 1


# ---------------------------------------------------------------------------
# masker_from_dict
# ---------------------------------------------------------------------------

def test_from_dict_builtin_credit_card():
    masker = masker_from_dict([{"builtin": "credit_card", "mask": "[CC]"}])
    result = masker.apply("card: 4111111111111111 done")
    assert "4111111111111111" not in result
    assert "[CC]" in result


def test_from_dict_builtin_email():
    masker = masker_from_dict([{"builtin": "email"}])
    result = masker.apply("contact user@example.com please")
    assert "user@example.com" not in result


def test_from_dict_custom_pattern():
    masker = masker_from_dict([{"pattern": r"(?P<value>SECRET-\w+)", "mask": "---"}])
    assert masker.apply("key=SECRET-abc") == "key=---"


def test_from_dict_unknown_builtin_raises():
    with pytest.raises(ValueError, match="Unknown built-in"):
        masker_from_dict([{"builtin": "nonexistent"}])


def test_from_dict_none_returns_empty_masker():
    masker = masker_from_dict(None)
    assert masker.apply("line") == "line"


# ---------------------------------------------------------------------------
# masker_from_config
# ---------------------------------------------------------------------------

def test_from_config_no_masking_attr():
    cfg = types.SimpleNamespace()
    masker = masker_from_config(cfg)
    assert masker.apply("line") == "line"


def test_from_config_list_masking():
    cfg = types.SimpleNamespace(
        masking=[{"builtin": "ipv4", "mask": "[IP]"}]
    )
    masker = masker_from_config(cfg)
    result = masker.apply("from 192.168.1.1 to 10.0.0.1")
    assert "192.168.1.1" not in result
    assert "[IP]" in result


def test_from_config_dict_masking():
    cfg = types.SimpleNamespace(
        masking={"rules": [{"builtin": "email", "mask": "[EMAIL]"}]}
    )
    masker = masker_from_config(cfg)
    result = masker.apply("send to admin@corp.io now")
    assert "admin@corp.io" not in result
