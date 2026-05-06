"""Tests for logsnap.alerting and logsnap.alert_config."""
from __future__ import annotations

import pytest

from logsnap.alerting import AlertManager, AlertRule
from logsnap.alert_config import load_alert_manager, _rule_from_dict


# ---------------------------------------------------------------------------
# AlertRule unit tests
# ---------------------------------------------------------------------------

def test_alert_rule_fires_when_threshold_reached():
    rule = AlertRule(name="r", source="app", threshold=3, window=10.0, cooldown=0.0)
    assert rule.record(0.0) is False
    assert rule.record(1.0) is False
    assert rule.record(2.0) is True  # 3rd hit within window


def test_alert_rule_does_not_fire_outside_window():
    rule = AlertRule(name="r", source="app", threshold=3, window=5.0, cooldown=0.0)
    rule.record(0.0)
    rule.record(1.0)
    # third event is outside the 5-second window of the first two
    assert rule.record(10.0) is False


def test_alert_rule_respects_cooldown():
    rule = AlertRule(name="r", source="app", threshold=2, window=10.0, cooldown=30.0)
    rule.record(0.0)
    rule.record(1.0)   # fires, resets
    # immediately try to fire again
    rule.record(2.0)
    assert rule.record(3.0) is False  # still in cooldown


def test_alert_rule_resets_timestamps_after_fire():
    rule = AlertRule(name="r", source="app", threshold=2, window=10.0, cooldown=0.0)
    rule.record(0.0)
    rule.record(1.0)   # fires → timestamps cleared
    assert rule.record(2.0) is False  # only 1 event after reset


# ---------------------------------------------------------------------------
# AlertManager tests
# ---------------------------------------------------------------------------

def test_manager_dispatches_to_handler():
    fired = []
    rule = AlertRule(name="r", source="app", threshold=2, window=10.0, cooldown=0.0)
    mgr = AlertManager(handler=lambda r, t: fired.append(r.name))
    mgr.add_rule(rule)

    mgr.notify("app", ts=0.0)
    mgr.notify("app", ts=1.0)
    assert fired == ["r"]


def test_manager_wildcard_source_matches_all():
    fired = []
    rule = AlertRule(name="w", source="*", threshold=2, window=10.0, cooldown=0.0)
    mgr = AlertManager(handler=lambda r, t: fired.append(r.name))
    mgr.add_rule(rule)

    mgr.notify("fileA", ts=0.0)
    mgr.notify("fileB", ts=1.0)
    assert fired == ["w"]


def test_manager_ignores_unrelated_source():
    fired = []
    rule = AlertRule(name="r", source="app", threshold=2, window=10.0, cooldown=0.0)
    mgr = AlertManager(handler=lambda r, t: fired.append(r.name))
    mgr.add_rule(rule)

    mgr.notify("other", ts=0.0)
    mgr.notify("other", ts=1.0)
    assert fired == []


def test_manager_remove_rule():
    fired = []
    rule = AlertRule(name="r", source="*", threshold=1, window=10.0, cooldown=0.0)
    mgr = AlertManager(handler=lambda r, t: fired.append(r.name))
    mgr.add_rule(rule)
    mgr.remove_rule("r")
    mgr.notify("app", ts=0.0)
    assert fired == []


# ---------------------------------------------------------------------------
# alert_config tests
# ---------------------------------------------------------------------------

def test_rule_from_dict_basic():
    d = {"name": "x", "source": "srv", "threshold": 5, "window": 20}
    rule = _rule_from_dict(d)
    assert rule.name == "x"
    assert rule.threshold == 5
    assert rule.cooldown == 60.0  # default


def test_rule_from_dict_missing_key():
    with pytest.raises(ValueError, match="missing keys"):
        _rule_from_dict({"name": "x", "source": "srv"})


def test_load_alert_manager_populates_rules():
    cfg = {
        "alerts": [
            {"name": "a", "source": "f1", "threshold": 3, "window": 10},
            {"name": "b", "source": "f2", "threshold": 5, "window": 30, "cooldown": 120},
        ]
    }
    mgr = load_alert_manager(cfg)
    names = {r.name for r in mgr.rules()}
    assert names == {"a", "b"}


def test_load_alert_manager_empty_config():
    mgr = load_alert_manager({})
    assert mgr.rules() == []
