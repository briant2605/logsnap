"""Tests for logsnap.parser (ParseRule, LineParser)."""
import re
import pytest
from logsnap.parser import LineParser, ParseRule


def _rule(name: str, pattern: str, defaults=None) -> ParseRule:
    return ParseRule(
        name=name,
        pattern=re.compile(pattern),
        defaults=defaults or {},
    )


# ---------------------------------------------------------------------------
# ParseRule
# ---------------------------------------------------------------------------

def test_parse_rule_returns_none_on_no_match():
    rule = _rule("r", r"(?P<level>ERROR)")
    assert rule.apply("INFO something") is None


def test_parse_rule_returns_groups_on_match():
    rule = _rule("r", r"(?P<level>\w+) (?P<msg>.+)")
    result = rule.apply("ERROR disk full")
    assert result == {"level": "ERROR", "msg": "disk full"}


def test_parse_rule_merges_defaults():
    rule = _rule("r", r"(?P<level>\w+)", defaults={"host": "localhost"})
    result = rule.apply("WARN")
    assert result["host"] == "localhost"
    assert result["level"] == "WARN"


def test_parse_rule_match_overrides_default():
    rule = _rule("r", r"(?P<host>\S+)", defaults={"host": "default"})
    result = rule.apply("myserver")
    assert result["host"] == "myserver"


# ---------------------------------------------------------------------------
# LineParser
# ---------------------------------------------------------------------------

def test_empty_parser_returns_raw():
    parser = LineParser()
    assert parser.parse("hello") == {"raw": "hello"}


def test_parser_returns_first_matching_rule():
    parser = LineParser()
    parser.add_rule(_rule("syslog", r"(?P<level>ERROR)"))
    parser.add_rule(_rule("fallback", r"(?P<level>\w+)"))
    result = parser.parse("ERROR boom")
    assert result["_rule"] == "syslog"
    assert result["level"] == "ERROR"


def test_parser_falls_through_to_second_rule():
    parser = LineParser()
    parser.add_rule(_rule("only_error", r"(?P<level>ERROR)"))
    parser.add_rule(_rule("any_level", r"(?P<level>\w+)"))
    result = parser.parse("INFO startup")
    assert result["_rule"] == "any_level"
    assert result["level"] == "INFO"


def test_parser_no_match_returns_raw():
    parser = LineParser()
    parser.add_rule(_rule("digits_only", r"^(?P<num>\d+)$"))
    result = parser.parse("not digits")
    assert result == {"raw": "not digits"}


def test_parser_rules_property():
    parser = LineParser()
    r = _rule("x", r"(?P<a>a)")
    parser.add_rule(r)
    assert parser.rules == [r]
