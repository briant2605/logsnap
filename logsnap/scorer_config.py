"""Load an EventScorer from a config dict or LogSnapConfig."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from logsnap.scorer import EventScorer, ScoreRule


def _rule_from_dict(d: Dict[str, Any]) -> ScoreRule:
    pattern = d["pattern"]
    score = float(d.get("score", 1.0))
    source: Optional[str] = d.get("source")
    return ScoreRule(pattern=pattern, score=score, source=source)


def scorer_from_dict(
    cfg: Optional[Dict[str, Any]],
    default_score: float = 0.0,
) -> EventScorer:
    """Build an EventScorer from a plain dict (e.g. parsed YAML/JSON).

    Expected shape::

        scorer:
          default_score: 0.0
          rules:
            - pattern: "ERROR"
              score: 10
            - pattern: "WARN"
              score: 3
              source: "app.log"
    """
    scorer = EventScorer(default_score=default_score)
    if not cfg:
        return scorer
    scorer = EventScorer(default_score=float(cfg.get("default_score", default_score)))
    rules: List[Dict[str, Any]] = cfg.get("rules") or []
    for raw in rules:
        scorer.add_rule(_rule_from_dict(raw))
    return scorer


def scorer_from_config(config: Any) -> EventScorer:
    """Build an EventScorer from a LogSnapConfig instance."""
    raw = getattr(config, "scorer", None)
    if isinstance(raw, dict):
        return scorer_from_dict(raw)
    return EventScorer()
