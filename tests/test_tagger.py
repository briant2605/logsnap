"""Tests for logsnap.tagger and logsnap.tagger_config."""
from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from logsnap.aggregator import LogEvent
from logsnap.tagger import TagRule, Tagger
from logsnap.tagger_config import tagger_from_config, tagger_from_dict


def _event(line: str, source: str = "app.log", tags=None) -> LogEvent:
    return LogEvent(source=source, line=line, timestamp=time.time(), tags=tags or {})


# ---------------------------------------------------------------------------
# TagRule
# ---------------------------------------------------------------------------

def test_tag_rule_matches_pattern():
    rule = TagRule(pattern=r"ERROR", tag="level", value="error")
    assert rule.matches(_event("2024-01-01 ERROR something broke"))


def test_tag_rule_no_match_leaves_event_unchanged():
    rule = TagRule(pattern=r"ERROR", tag="level", value="error")
    event = _event("INFO all good")
    assert not rule.matches(event)


def test_tag_rule_apply_injects_tag():
    rule = TagRule(pattern=r"WARN", tag="severity", value="warning")
    event = _event("WARN disk almost full")
    result = rule.apply(event)
    assert result.tags["severity"] == "warning"
    assert result.line == event.line
    assert result.source == event.source


def test_tag_rule_default_value_is_true():
    rule = TagRule(pattern=r"CRITICAL", tag="critical")
    event = _event("CRITICAL meltdown")
    result = rule.apply(event)
    assert result.tags["critical"] is True


def test_tag_rule_source_filter_restricts_match():
    rule = TagRule(pattern=r"ERROR", tag="level", source="db.log")
    assert not rule.matches(_event("ERROR oops", source="app.log"))
    assert rule.matches(_event("ERROR oops", source="db.log"))


def test_tag_rule_preserves_existing_tags():
    rule = TagRule(pattern=r"ERROR", tag="new_tag", value=42)
    event = _event("ERROR", tags={"existing": "yes"})
    result = rule.apply(event)
    assert result.tags["existing"] == "yes"
    assert result.tags["new_tag"] == 42


# ---------------------------------------------------------------------------
# Tagger
# ---------------------------------------------------------------------------

def test_tagger_no_rules_returns_event_unchanged():
    tagger = Tagger()
    event = _event("INFO hello")
    assert tagger.apply(event) is event


def test_tagger_applies_matching_rule():
    tagger = Tagger()
    tagger.add_rule(TagRule(pattern=r"ERROR", tag="level", value="error"))
    result = tagger.apply(_event("ERROR boom"))
    assert result.tags["level"] == "error"


def test_tagger_applies_multiple_rules_in_order():
    tagger = Tagger()
    tagger.add_rule(TagRule(pattern=r"ERROR", tag="level", value="error"))
    tagger.add_rule(TagRule(pattern=r"disk", tag="component", value="storage"))
    result = tagger.apply(_event("ERROR disk failure"))
    assert result.tags["level"] == "error"
    assert result.tags["component"] == "storage"


def test_tagger_add_rule_returns_self():
    tagger = Tagger()
    ret = tagger.add_rule(TagRule(pattern=r"x", tag="t"))
    assert ret is tagger


# ---------------------------------------------------------------------------
# tagger_from_dict / tagger_from_config
# ---------------------------------------------------------------------------

def test_none_returns_empty_tagger():
    tagger = tagger_from_dict(None)
    assert tagger.rules == []


def test_empty_list_returns_empty_tagger():
    tagger = tagger_from_dict([])
    assert tagger.rules == []


def test_single_rule_loaded():
    cfg = [{"pattern": "WARN", "tag": "level", "value": "warning"}]
    tagger = tagger_from_dict(cfg)
    assert len(tagger.rules) == 1
    result = tagger.apply(_event("WARN low memory"))
    assert result.tags["level"] == "warning"


def test_source_filter_loaded_from_dict():
    cfg = [{"pattern": "ERROR", "tag": "lvl", "source": "db.log"}]
    tagger = tagger_from_dict(cfg)
    assert tagger.rules[0].source == "db.log"


def test_tagger_from_config_reads_tagging_attr():
    cfg = SimpleNamespace(tagging=[{"pattern": "CRITICAL", "tag": "critical"}])
    tagger = tagger_from_config(cfg)
    assert len(tagger.rules) == 1


def test_tagger_from_config_missing_attr_returns_empty():
    cfg = SimpleNamespace()
    tagger = tagger_from_config(cfg)
    assert tagger.rules == []
