"""Tests for logsnap.enricher."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from logsnap.aggregator import LogEvent
from logsnap.enricher import EnrichRule, Enricher, enricher_from_dict


def _event(line: str, source: str = "app.log") -> LogEvent:
    return LogEvent(source=source, line=line, ts=time.time(), extra={})


# ---------------------------------------------------------------------------
# EnrichRule
# ---------------------------------------------------------------------------

def test_enrich_rule_adds_tag_on_match():
    rule = EnrichRule(tag="severity", pattern=r"ERROR", value="error")
    ev = _event("2024-01-01 ERROR something blew up")
    rule.apply(ev)
    assert ev.extra["severity"] == "error"


def test_enrich_rule_no_tag_when_no_match():
    rule = EnrichRule(tag="severity", pattern=r"ERROR", value="error")
    ev = _event("2024-01-01 INFO all good")
    rule.apply(ev)
    assert "severity" not in ev.extra


def test_enrich_rule_default_value_is_true():
    rule = EnrichRule(tag="has_warning", pattern=r"WARN")
    ev = _event("WARN disk space low")
    rule.apply(ev)
    assert ev.extra["has_warning"] == "true"


def test_enrich_rule_returns_event():
    rule = EnrichRule(tag="x", pattern=r"x")
    ev = _event("x marks the spot")
    returned = rule.apply(ev)
    assert returned is ev


def test_enrich_rule_repr_contains_fields():
    rule = EnrichRule(tag="env", pattern=r"prod", value="production")
    r = repr(rule)
    assert "env" in r
    assert "prod" in r
    assert "production" in r


# ---------------------------------------------------------------------------
# Enricher
# ---------------------------------------------------------------------------

def test_enricher_applies_all_rules():
    enricher = Enricher([
        EnrichRule(tag="is_error", pattern=r"ERROR"),
        EnrichRule(tag="is_db", pattern=r"database"),
    ])
    ev = _event("ERROR database connection failed")
    enricher.enrich(ev)
    assert ev.extra["is_error"] == "true"
    assert ev.extra["is_db"] == "true"


def test_enricher_no_rules_leaves_event_unchanged():
    enricher = Enricher()
    ev = _event("INFO startup complete")
    enricher.enrich(ev)
    assert ev.extra == {}


def test_enricher_add_rule_appends():
    enricher = Enricher()
    rule = EnrichRule(tag="k", pattern=r"k")
    enricher.add_rule(rule)
    assert rule in enricher.rules


def test_enricher_rules_property_returns_copy():
    enricher = Enricher([EnrichRule(tag="a", pattern=r"a")])
    copy = enricher.rules
    copy.clear()
    assert len(enricher.rules) == 1


def test_enricher_repr():
    enricher = Enricher([EnrichRule(tag="t", pattern=r"t")])
    assert "Enricher" in repr(enricher)


# ---------------------------------------------------------------------------
# enricher_from_dict
# ---------------------------------------------------------------------------

def test_enricher_from_dict_builds_rules():
    cfg = [
        {"tag": "level", "pattern": "ERROR", "value": "error"},
        {"tag": "slow", "pattern": r"took \d{4,}ms"},
    ]
    enricher = enricher_from_dict(cfg)
    assert len(enricher.rules) == 2


def test_enricher_from_dict_none_returns_empty():
    enricher = enricher_from_dict(None)
    assert enricher.rules == []


def test_enricher_from_dict_fires_correctly():
    cfg = [{"tag": "critical", "pattern": "CRITICAL", "value": "yes"}]
    enricher = enricher_from_dict(cfg)
    ev = _event("CRITICAL system failure")
    enricher.enrich(ev)
    assert ev.extra["critical"] == "yes"
