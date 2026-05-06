"""Tests for logsnap.redactor."""

import re
import pytest

from logsnap.redactor import RedactRule, Redactor


# ---------------------------------------------------------------------------
# RedactRule
# ---------------------------------------------------------------------------

def test_redact_rule_replaces_match():
    rule = RedactRule(name="secret", pattern=re.compile(r"password=\S+"))
    result = rule.apply("login password=hunter2 ok")
    assert result == "login [REDACTED] ok"


def test_redact_rule_custom_replacement():
    rule = RedactRule(
        name="token",
        pattern=re.compile(r"tok_[A-Za-z0-9]+"),
        replacement="[TOKEN]",
    )
    result = rule.apply("auth tok_abc123 granted")
    assert result == "auth [TOKEN] granted"


def test_redact_rule_no_match_returns_original():
    rule = RedactRule(name="ip", pattern=re.compile(r"\d{1,3}(?:\.\d{1,3}){3}"))
    line = "no ip address here"
    assert rule.apply(line) == line


def test_redact_rule_replaces_all_occurrences():
    rule = RedactRule(name="num", pattern=re.compile(r"\d+"), replacement="#")
    assert rule.apply("foo 123 bar 456") == "foo # bar #"


# ---------------------------------------------------------------------------
# Redactor – basic
# ---------------------------------------------------------------------------

def test_redactor_empty_rules_returns_line_unchanged():
    r = Redactor()
    assert r.redact("hello world") == "hello world"


def test_redactor_applies_rules_in_order():
    r = Redactor()
    r.add_rule("step1", r"foo", "bar")
    r.add_rule("step2", r"bar", "baz")
    # 'foo' → 'bar' → 'baz'
    assert r.redact("foo") == "baz"


def test_redactor_add_rule_custom():
    r = Redactor()
    r.add_rule("api_key", r"key=[A-Za-z0-9]+", "key=[REDACTED]")
    assert r.redact("request key=abc123 sent") == "request key=[REDACTED] sent"


# ---------------------------------------------------------------------------
# Redactor – presets
# ---------------------------------------------------------------------------

def test_preset_ipv4():
    r = Redactor.from_presets(["ipv4"])
    assert r.redact("connect from 192.168.1.1 ok") == "connect from [IP] ok"


def test_preset_email():
    r = Redactor.from_presets(["email"])
    result = r.redact("user user@example.com logged in")
    assert "[EMAIL]" in result
    assert "user@example.com" not in result


def test_preset_bearer_token():
    r = Redactor.from_presets(["bearer_token"])
    line = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig"
    result = r.redact(line)
    assert "Bearer [REDACTED]" in result
    assert "eyJ" not in result


def test_preset_credit_card():
    r = Redactor.from_presets(["credit_card"])
    result = r.redact("card 4111111111111111 charged")
    assert "[CARD]" in result


def test_unknown_preset_raises():
    with pytest.raises(ValueError, match="Unknown redaction preset"):
        Redactor.from_presets(["ssn"])


def test_multiple_presets_combined():
    r = Redactor.from_presets(["ipv4", "email"])
    line = "src 10.0.0.1 user admin@corp.io"
    result = r.redact(line)
    assert "[IP]" in result
    assert "[EMAIL]" in result
    assert "10.0.0.1" not in result
    assert "admin@corp.io" not in result


def test_rules_property_returns_copy():
    r = Redactor.from_presets(["ipv4"])
    rules = r.rules
    assert len(rules) == 1
    rules.clear()          # mutating the returned list must not affect the Redactor
    assert len(r.rules) == 1
