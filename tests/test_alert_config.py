"""Extra integration-style tests for alert_config + alerting interaction."""
from __future__ import annotations

from logsnap.alert_config import load_alert_manager


def test_loaded_rules_fire_correctly():
    """Rules loaded from config actually trigger the handler when lines arrive."""
    fired = []
    cfg = {
        "alerts": [
            {"name": "burst", "source": "web", "threshold": 3, "window": 10, "cooldown": 0},
        ]
    }
    mgr = load_alert_manager(cfg, handler=lambda r, t: fired.append((r.name, t)))

    for ts in (0.0, 1.0, 2.0):
        mgr.notify("web", ts=ts)

    assert len(fired) == 1
    assert fired[0][0] == "burst"


def test_multiple_rules_independent():
    """Two rules for different sources fire independently."""
    fired = []
    cfg = {
        "alerts": [
            {"name": "r1", "source": "a", "threshold": 2, "window": 10, "cooldown": 0},
            {"name": "r2", "source": "b", "threshold": 2, "window": 10, "cooldown": 0},
        ]
    }
    mgr = load_alert_manager(cfg, handler=lambda r, t: fired.append(r.name))

    mgr.notify("a", ts=0.0)
    mgr.notify("b", ts=0.0)
    mgr.notify("a", ts=1.0)  # r1 fires
    mgr.notify("b", ts=1.0)  # r2 fires

    assert sorted(fired) == ["r1", "r2"]


def test_cooldown_from_config_respected():
    """Custom cooldown loaded from config prevents double-firing."""
    fired = []
    cfg = {
        "alerts": [
            {"name": "c", "source": "*", "threshold": 2, "window": 60, "cooldown": 999},
        ]
    }
    mgr = load_alert_manager(cfg, handler=lambda r, t: fired.append(r.name))

    # first burst
    mgr.notify("x", ts=0.0)
    mgr.notify("x", ts=1.0)  # fires
    # second burst immediately after
    mgr.notify("x", ts=2.0)
    mgr.notify("x", ts=3.0)  # still in cooldown — should NOT fire

    assert fired == ["c"]
