"""Tests for logsnap.classifier_config."""
from __future__ import annotations

import pytest

from logsnap.aggregator import LogEvent
from logsnap.classifier_config import classifier_from_config, classifier_from_dict


def _event(line: str, source: str = "app") -> LogEvent:
    return LogEvent(source=source, line=line, tags={})


# ---------------------------------------------------------------------------
# classifier_from_dict
# ---------------------------------------------------------------------------

def test_none_returns_none():
    assert classifier_from_dict(None) is None


def test_empty_list_returns_none_without_default():
    assert classifier_from_dict([]) is None


def test_empty_list_with_default_returns_classifier():
    clf = classifier_from_dict([], default_category="misc")
    assert clf is not None
    result = clf.classify(_event("anything"))
    assert result.tags["category"] == "misc"


def test_single_rule_loaded():
    rules = [{"pattern": "ERROR", "category": "error"}]
    clf = classifier_from_dict(rules)
    assert clf is not None
    result = clf.classify(_event("ERROR: bad"))
    assert result.tags["category"] == "error"


def test_source_filter_loaded():
    rules = [{"pattern": "WARN", "category": "warning", "source": "db"}]
    clf = classifier_from_dict(rules)
    assert clf is not None
    # wrong source — should not match
    result = clf.classify(_event("WARN: slow", source="app"))
    assert "category" not in result.tags
    # correct source — should match
    result = clf.classify(_event("WARN: slow", source="db"))
    assert result.tags["category"] == "warning"


def test_multiple_rules_first_wins():
    rules = [
        {"pattern": "ERROR", "category": "error"},
        {"pattern": "ERROR", "category": "critical"},
    ]
    clf = classifier_from_dict(rules)
    result = clf.classify(_event("ERROR: oops"))
    assert result.tags["category"] == "error"


# ---------------------------------------------------------------------------
# classifier_from_config
# ---------------------------------------------------------------------------

class _FakeConfig:
    def __init__(self, raw):
        self.classifier = raw


def test_none_config_returns_none():
    assert classifier_from_config(_FakeConfig(None)) is None


def test_config_rules_loaded():
    cfg = _FakeConfig({
        "rules": [{"pattern": "CRIT", "category": "critical"}],
        "default_category": "info",
    })
    clf = classifier_from_config(cfg)
    assert clf is not None
    result = clf.classify(_event("CRIT: meltdown"))
    assert result.tags["category"] == "critical"


def test_config_default_category_used():
    cfg = _FakeConfig({"rules": [], "default_category": "general"})
    clf = classifier_from_config(cfg)
    assert clf is not None
    result = clf.classify(_event("random line"))
    assert result.tags["category"] == "general"


def test_missing_classifier_attr_returns_none():
    class _NoCfg:
        pass
    assert classifier_from_config(_NoCfg()) is None
