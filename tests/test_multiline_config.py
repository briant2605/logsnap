"""Tests for multiline_config loader."""
from __future__ import annotations

import pytest

from logsnap.multiline import MultilineConfig
from logsnap.multiline_config import multiline_from_config, multiline_from_dict


# ---------------------------------------------------------------------------
# multiline_from_dict
# ---------------------------------------------------------------------------

def test_none_returns_none():
    assert multiline_from_dict(None) is None


def test_empty_dict_returns_none():
    assert multiline_from_dict({}) is None


def test_start_pattern_loaded():
    cfg = multiline_from_dict({"start_pattern": r"^\d"})
    assert isinstance(cfg, MultilineConfig)
    assert cfg.start_pattern == r"^\d"


def test_max_lines_loaded():
    cfg = multiline_from_dict({"start_pattern": r"^\S", "max_lines": 100})
    assert cfg.max_lines == 100


def test_flush_timeout_loaded():
    cfg = multiline_from_dict({"start_pattern": r"^\S", "flush_timeout": 3.5})
    assert cfg.flush_timeout == pytest.approx(3.5)


def test_invalid_max_lines_raises():
    with pytest.raises(ValueError, match="max_lines"):
        multiline_from_dict({"start_pattern": r"^\S", "max_lines": 0})


def test_negative_flush_timeout_raises():
    with pytest.raises(ValueError, match="flush_timeout"):
        multiline_from_dict({"start_pattern": r"^\S", "flush_timeout": -1})


# ---------------------------------------------------------------------------
# multiline_from_config
# ---------------------------------------------------------------------------

class _FakeCfg:
    def __init__(self, multiline):
        self.multiline = multiline


def test_from_config_none_attribute_returns_none():
    assert multiline_from_config(_FakeCfg(None)) is None


def test_from_config_dict_attribute_returns_config():
    result = multiline_from_config(_FakeCfg({"start_pattern": r"^ERROR"}))
    assert isinstance(result, MultilineConfig)
    assert result.start_pattern == r"^ERROR"


def test_from_config_missing_attribute_returns_none():
    class _NoCfg:
        pass
    assert multiline_from_config(_NoCfg()) is None
