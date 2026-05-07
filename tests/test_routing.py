"""Tests for logsnap.routing."""
from __future__ import annotations

from logsnap.aggregator import LogEvent
from logsnap.routing import EventRouter, RouteRule


def _event(line: str, source: str = "app.log") -> LogEvent:
    return LogEvent(source=source, line=line)


# ---------------------------------------------------------------------------
# RouteRule
# ---------------------------------------------------------------------------

def test_route_rule_matches_pattern():
    rule = RouteRule(channel="errors", pattern=r"ERROR")
    assert rule.matches(_event("2024-01-01 ERROR something broke"))
    assert not rule.matches(_event("2024-01-01 INFO all good"))


def test_route_rule_matches_source():
    rule = RouteRule(channel="auth", source="auth.log")
    assert rule.matches(_event("login failed", source="auth.log"))
    assert not rule.matches(_event("login failed", source="app.log"))


def test_route_rule_matches_pattern_and_source():
    rule = RouteRule(channel="auth_errors", pattern=r"FAIL", source="auth.log")
    assert rule.matches(_event("FAIL attempt", source="auth.log"))
    assert not rule.matches(_event("FAIL attempt", source="app.log"))
    assert not rule.matches(_event("OK", source="auth.log"))


def test_route_rule_no_constraints_matches_all():
    rule = RouteRule(channel="catch_all")
    assert rule.matches(_event("anything"))


def test_route_rule_repr():
    rule = RouteRule(channel="errors", pattern="ERROR")
    assert "errors" in repr(rule)
    assert "ERROR" in repr(rule)


# ---------------------------------------------------------------------------
# EventRouter
# ---------------------------------------------------------------------------

def test_router_dispatches_to_matching_channel():
    router = EventRouter()
    router.add_rule(RouteRule(channel="errors", pattern=r"ERROR"))
    received: list = []
    router.register("errors", received.append)

    router.route(_event("ERROR boom"))
    assert len(received) == 1
    assert received[0].line == "ERROR boom"


def test_router_falls_back_to_default():
    router = EventRouter()
    router.add_rule(RouteRule(channel="errors", pattern=r"ERROR"))
    defaults: list = []
    router.register(EventRouter.DEFAULT_CHANNEL, defaults.append)

    router.route(_event("INFO all fine"))
    assert len(defaults) == 1


def test_router_first_matching_rule_wins():
    router = EventRouter()
    router.add_rule(RouteRule(channel="first", pattern=r"ERROR"))
    router.add_rule(RouteRule(channel="second", pattern=r"ERROR"))
    first_ch: list = []
    second_ch: list = []
    router.register("first", first_ch.append)
    router.register("second", second_ch.append)

    router.route(_event("ERROR clash"))
    assert len(first_ch) == 1
    assert len(second_ch) == 0


def test_router_returns_channel_name():
    router = EventRouter()
    router.add_rule(RouteRule(channel="errors", pattern=r"ERROR"))
    ch = router.route(_event("ERROR here"))
    assert ch == "errors"


def test_router_returns_default_when_no_match():
    router = EventRouter()
    ch = router.route(_event("INFO nothing special"))
    assert ch == EventRouter.DEFAULT_CHANNEL


def test_router_multiple_handlers_same_channel():
    router = EventRouter()
    router.add_rule(RouteRule(channel="out", pattern=r"HIT"))
    a: list = []
    b: list = []
    router.register("out", a.append)
    router.register("out", b.append)

    router.route(_event("HIT target"))
    assert len(a) == 1
    assert len(b) == 1


def test_router_repr_contains_counts():
    router = EventRouter()
    router.add_rule(RouteRule(channel="x"))
    router.register("x", lambda e: None)
    r = repr(router)
    assert "rules=1" in r
    assert "x" in r
