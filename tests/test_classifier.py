"""Tests for logsnap.classifier."""
from __future__ import annotations

import pytest

from logsnap.aggregator import LogEvent
from logsnap.classifier import ClassifyRule, EventClassifier


def _event(line: str, source: str = "app", tags: dict | None = None) -> LogEvent:
    return LogEvent(source=source, line=line, tags=tags or {})


# ---------------------------------------------------------------------------
# ClassifyRule
# ---------------------------------------------------------------------------

def test_classify_rule_matches_pattern():
    rule = ClassifyRule(pattern=r"ERROR", category="error")
    assert rule.matches(_event("ERROR: something bad"))


def test_classify_rule_no_match_returns_false():
    rule = ClassifyRule(pattern=r"ERROR", category="error")
    assert not rule.matches(_event("INFO: all good"))


def test_classify_rule_source_filter_respected():
    rule = ClassifyRule(pattern=r"WARN", category="warning", source="db")
    assert not rule.matches(_event("WARN: slow query", source="app"))
    assert rule.matches(_event("WARN: slow query", source="db"))


def test_classify_rule_apply_injects_category():
    rule = ClassifyRule(pattern=r"ERROR", category="error")
    event = _event("ERROR: boom")
    result = rule.apply(event)
    assert result.tags["category"] == "error"


def test_classify_rule_apply_preserves_existing_tags():
    rule = ClassifyRule(pattern=r"ERROR", category="error")
    event = _event("ERROR: boom", tags={"env": "prod"})
    result = rule.apply(event)
    assert result.tags["env"] == "prod"
    assert result.tags["category"] == "error"


# ---------------------------------------------------------------------------
# EventClassifier
# ---------------------------------------------------------------------------

def test_first_matching_rule_wins():
    clf = EventClassifier()
    clf.add_rule(ClassifyRule(pattern=r"ERROR", category="error"))
    clf.add_rule(ClassifyRule(pattern=r"ERROR", category="critical"))
    result = clf.classify(_event("ERROR: oops"))
    assert result.tags["category"] == "error"


def test_no_match_returns_event_unchanged():
    clf = EventClassifier()
    clf.add_rule(ClassifyRule(pattern=r"ERROR", category="error"))
    event = _event("DEBUG: verbose")
    result = clf.classify(event)
    assert "category" not in result.tags


def test_default_category_applied_when_no_rule_matches():
    clf = EventClassifier(default_category="unknown")
    result = clf.classify(_event("DEBUG: verbose"))
    assert result.tags["category"] == "unknown"


def test_callback_invoked_on_match():
    fired: list = []
    clf = EventClassifier()
    clf.add_rule(ClassifyRule(pattern=r"WARN", category="warning"))
    clf.on_classify(lambda ev, cat: fired.append(cat))
    clf.classify(_event("WARN: disk low"))
    assert fired == ["warning"]


def test_callback_not_invoked_when_no_match():
    fired: list = []
    clf = EventClassifier()
    clf.add_rule(ClassifyRule(pattern=r"ERROR", category="error"))
    clf.on_classify(lambda ev, cat: fired.append(cat))
    clf.classify(_event("INFO: ok"))
    assert fired == []


def test_categories_returns_counts():
    clf = EventClassifier()
    clf.add_rule(ClassifyRule(pattern=r"ERROR", category="error"))
    clf.add_rule(ClassifyRule(pattern=r"CRITICAL", category="error"))
    clf.add_rule(ClassifyRule(pattern=r"WARN", category="warning"))
    counts = clf.categories()
    assert counts["error"] == 2
    assert counts["warning"] == 1


def test_empty_classifier_returns_event_unchanged():
    clf = EventClassifier()
    event = _event("hello world")
    assert clf.classify(event) is event
