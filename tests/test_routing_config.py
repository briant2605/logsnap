"""Tests for logsnap.routing_config."""
from __future__ import annotations

import pytest

from logsnap.aggregator import LogEvent
from logsnap.routing import EventRouter
from logsnap.routing_config import router_from_dict


def _event(line: str, source: str = "app.log") -> LogEvent:
    return LogEvent(source=source, line=line)


def test_none_config_returns_empty_router():
    router = router_from_dict(None)
    assert isinstance(router, EventRouter)


def test_empty_rules_returns_router():
    router = router_from_dict({"rules": []})
    assert isinstance(router, EventRouter)


def test_single_rule_loaded():
    cfg = {"rules": [{"channel": "errors", "pattern": "ERROR"}]}
    router = router_from_dict(cfg)
    received: list = []
    router.register("errors", received.append)
    router.route(_event("ERROR something"))
    assert len(received) == 1


def test_source_rule_loaded():
    cfg = {"rules": [{"channel": "auth", "source": "auth.log"}]}
    router = router_from_dict(cfg)
    received: list = []
    router.register("auth", received.append)
    router.route(_event("login ok", source="auth.log"))
    router.route(_event("login ok", source="app.log"))
    assert len(received) == 1


def test_multiple_rules_ordered():
    cfg = {
        "rules": [
            {"channel": "critical", "pattern": "CRITICAL"},
            {"channel": "errors", "pattern": "ERROR"},
        ]
    }
    router = router_from_dict(cfg)
    crit: list = []
    errs: list = []
    router.register("critical", crit.append)
    router.register("errors", errs.append)

    router.route(_event("CRITICAL meltdown"))
    router.route(_event("ERROR minor"))
    assert len(crit) == 1
    assert len(errs) == 1


def test_missing_channel_raises():
    with pytest.raises(ValueError, match="channel"):
        router_from_dict({"rules": [{"pattern": "ERROR"}]})


def test_default_channel_used_when_no_rule_matches():
    cfg = {"rules": [{"channel": "errors", "pattern": "ERROR"}]}
    router = router_from_dict(cfg)
    defaults: list = []
    router.register(EventRouter.DEFAULT_CHANNEL, defaults.append)
    router.route(_event("INFO nothing"))
    assert len(defaults) == 1
