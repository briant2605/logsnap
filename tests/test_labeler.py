"""Tests for logsnap.labeler."""
import pytest

from logsnap.aggregator import LogEvent
from logsnap.labeler import LabelRule, Labeler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event(source: str = "app", line: str = "hello", **tags) -> LogEvent:
    return LogEvent(source=source, line=line, tags=dict(tags))


# ---------------------------------------------------------------------------
# LabelRule.matches
# ---------------------------------------------------------------------------

def test_label_rule_no_sources_matches_all():
    rule = LabelRule(key="env", value="prod")
    assert rule.matches(_event(source="app"))
    assert rule.matches(_event(source="worker"))


def test_label_rule_source_filter_matches():
    rule = LabelRule(key="env", value="prod", sources=["app"])
    assert rule.matches(_event(source="app"))


def test_label_rule_source_filter_no_match():
    rule = LabelRule(key="env", value="prod", sources=["app"])
    assert not rule.matches(_event(source="worker"))


# ---------------------------------------------------------------------------
# LabelRule.apply
# ---------------------------------------------------------------------------

def test_label_rule_injects_key():
    rule = LabelRule(key="env", value="staging")
    result = rule.apply(_event())
    assert result.tags["env"] == "staging"


def test_label_rule_does_not_mutate_original():
    original = _event()
    rule = LabelRule(key="env", value="prod")
    result = rule.apply(original)
    assert "env" not in original.tags
    assert result.tags["env"] == "prod"


def test_label_rule_skips_non_matching_source():
    rule = LabelRule(key="env", value="prod", sources=["db"])
    result = rule.apply(_event(source="app"))
    assert "env" not in result.tags


def test_label_rule_value_types():
    rule = LabelRule(key="count", value=42)
    result = rule.apply(_event())
    assert result.tags["count"] == 42


def test_label_rule_repr():
    rule = LabelRule(key="env", value="prod", sources=["app"])
    r = repr(rule)
    assert "env" in r
    assert "prod" in r
    assert "app" in r


# ---------------------------------------------------------------------------
# Labeler
# ---------------------------------------------------------------------------

def test_labeler_empty_returns_event_unchanged():
    labeler = Labeler()
    ev = _event()
    assert labeler.apply(ev) is ev


def test_labeler_applies_single_rule():
    labeler = Labeler([LabelRule(key="region", value="us-east-1")])
    result = labeler.apply(_event())
    assert result.tags["region"] == "us-east-1"


def test_labeler_chains_rules_in_order():
    labeler = Labeler([
        LabelRule(key="env", value="prod"),
        LabelRule(key="tier", value="backend"),
    ])
    result = labeler.apply(_event())
    assert result.tags["env"] == "prod"
    assert result.tags["tier"] == "backend"


def test_labeler_add_rule_appends():
    labeler = Labeler()
    labeler.add_rule(LabelRule(key="x", value=1))
    assert len(labeler.rules) == 1


def test_labeler_rules_property_is_copy():
    labeler = Labeler([LabelRule(key="a", value=1)])
    rules = labeler.rules
    rules.clear()
    assert len(labeler.rules) == 1


def test_labeler_repr_contains_class():
    labeler = Labeler([LabelRule(key="env", value="dev")])
    assert "Labeler" in repr(labeler)
