"""Tests for logsnap.scorer and logsnap.scorer_config."""
import pytest

from logsnap.aggregator import LogEvent
from logsnap.scorer import EventScorer, ScoreRule
from logsnap.scorer_config import scorer_from_config, scorer_from_dict


def _event(line: str, source: str = "test.log") -> LogEvent:
    return LogEvent(source=source, line=line)


# ---------------------------------------------------------------------------
# ScoreRule
# ---------------------------------------------------------------------------

def test_score_rule_matches_pattern():
    rule = ScoreRule(pattern=r"ERROR", score=5.0)
    assert rule.matches(_event("ERROR: something bad"))


def test_score_rule_no_match_returns_false():
    rule = ScoreRule(pattern=r"ERROR", score=5.0)
    assert not rule.matches(_event("INFO: all good"))


def test_score_rule_source_filter_respected():
    rule = ScoreRule(pattern=r"WARN", score=2.0, source="app.log")
    assert rule.matches(_event("WARN: low disk", source="app.log"))
    assert not rule.matches(_event("WARN: low disk", source="other.log"))


# ---------------------------------------------------------------------------
# EventScorer
# ---------------------------------------------------------------------------

def test_default_score_returned_when_no_rules():
    scorer = EventScorer(default_score=1.0)
    assert scorer.score(_event("anything")) == 1.0


def test_default_score_returned_when_no_match():
    scorer = EventScorer(default_score=0.5)
    scorer.add_rule(ScoreRule(pattern=r"ERROR", score=10.0))
    assert scorer.score(_event("INFO: ok")) == 0.5


def test_matching_rule_adds_to_default():
    scorer = EventScorer(default_score=1.0)
    scorer.add_rule(ScoreRule(pattern=r"ERROR", score=9.0))
    assert scorer.score(_event("ERROR: boom")) == pytest.approx(10.0)


def test_multiple_rules_accumulate():
    scorer = EventScorer()
    scorer.add_rule(ScoreRule(pattern=r"ERROR", score=10.0))
    scorer.add_rule(ScoreRule(pattern=r"critical", score=5.0))
    assert scorer.score(_event("ERROR critical failure")) == pytest.approx(15.0)


def test_negative_default_score_raises():
    with pytest.raises(ValueError):
        EventScorer(default_score=-1.0)


def test_rules_list_returns_copy():
    scorer = EventScorer()
    scorer.add_rule(ScoreRule(pattern=r"X", score=1.0))
    rules = scorer.rules()
    rules.clear()
    assert len(scorer.rules()) == 1


def test_on_score_callback_invoked():
    received = []
    scorer = EventScorer()
    scorer.add_rule(ScoreRule(pattern=r"ERR", score=3.0))
    scorer.on_score(lambda ev, s: received.append((ev.line, s)))
    scorer.score(_event("ERR: oops"))
    assert received == [("ERR: oops", 3.0)]


def test_on_score_callback_called_even_on_default():
    received = []
    scorer = EventScorer(default_score=2.0)
    scorer.on_score(lambda ev, s: received.append(s))
    scorer.score(_event("INFO: fine"))
    assert received == [2.0]


# ---------------------------------------------------------------------------
# scorer_config
# ---------------------------------------------------------------------------

def test_none_config_returns_default_scorer():
    scorer = scorer_from_dict(None)
    assert isinstance(scorer, EventScorer)
    assert scorer.score(_event("anything")) == 0.0


def test_rules_loaded_from_dict():
    cfg = {"rules": [{"pattern": "ERROR", "score": 7}]}
    scorer = scorer_from_dict(cfg)
    assert scorer.score(_event("ERROR: bad")) == pytest.approx(7.0)


def test_default_score_loaded_from_dict():
    cfg = {"default_score": 1.5, "rules": []}
    scorer = scorer_from_dict(cfg)
    assert scorer.score(_event("INFO: ok")) == pytest.approx(1.5)


def test_scorer_from_config_uses_scorer_key():
    class Cfg:
        scorer = {"default_score": 0.0, "rules": [{"pattern": "CRIT", "score": 20}]}

    scorer = scorer_from_config(Cfg())
    assert scorer.score(_event("CRIT: meltdown")) == pytest.approx(20.0)


def test_scorer_from_config_missing_key_returns_default():
    class Cfg:
        pass

    scorer = scorer_from_config(Cfg())
    assert scorer.score(_event("whatever")) == 0.0
