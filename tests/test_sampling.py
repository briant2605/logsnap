"""Tests for logsnap.sampling and logsnap.sampling_config."""
from __future__ import annotations

import pytest

from logsnap.sampling import LineSampler, SamplerStats
from logsnap.sampling_config import sampler_from_dict, sampler_from_config


# ---------------------------------------------------------------------------
# SamplerStats

def test_stats_to_dict_defaults():
    s = SamplerStats()
    assert s.to_dict() == {"seen": 0, "emitted": 0, "dropped": 0}


# ---------------------------------------------------------------------------
# LineSampler — basic

def test_rate_1_always_allows():
    sampler = LineSampler(rate=1)
    for _ in range(20):
        assert sampler.should_emit("src") is True


def test_invalid_rate_raises():
    with pytest.raises(ValueError):
        LineSampler(rate=0)
    with pytest.raises(ValueError):
        LineSampler(rate=-3)


def test_rate_n_emits_every_nth():
    sampler = LineSampler(rate=3)
    results = [sampler.should_emit("app") for _ in range(9)]
    # expect: True False False True False False True False False
    assert results == [True, False, False, True, False, False, True, False, False]


def test_sources_are_independent():
    sampler = LineSampler(rate=2)
    # first event for each source should be emitted
    assert sampler.should_emit("a") is True
    assert sampler.should_emit("b") is True
    # second event for each should be dropped
    assert sampler.should_emit("a") is False
    assert sampler.should_emit("b") is False


# ---------------------------------------------------------------------------
# Stats tracking

def test_stats_track_seen_emitted_dropped():
    sampler = LineSampler(rate=3)
    for _ in range(6):
        sampler.should_emit("svc")
    st = sampler.stats("svc")
    assert st["seen"] == 6
    assert st["emitted"] == 2
    assert st["dropped"] == 4


def test_stats_all_sources():
    sampler = LineSampler(rate=2)
    sampler.should_emit("x")
    sampler.should_emit("y")
    all_stats = sampler.stats()
    assert "x" in all_stats
    assert "y" in all_stats


# ---------------------------------------------------------------------------
# Reset

def test_reset_specific_source():
    sampler = LineSampler(rate=3)
    sampler.should_emit("s")  # counter -> 1
    sampler.should_emit("s")  # counter -> 2
    sampler.reset("s")
    # after reset first event should be emitted again
    assert sampler.should_emit("s") is True


def test_reset_all_sources():
    sampler = LineSampler(rate=4)
    for _ in range(3):
        sampler.should_emit("p")
        sampler.should_emit("q")
    sampler.reset()
    assert sampler.stats() == {}


# ---------------------------------------------------------------------------
# Config helpers

def test_sampler_from_dict_default_rate():
    sampler = sampler_from_dict({})
    assert sampler.rate == 1


def test_sampler_from_dict_custom_rate():
    sampler = sampler_from_dict({"sampling": {"rate": 5}})
    assert sampler.rate == 5


def test_sampler_from_config_uses_to_dict():
    class FakeConfig:
        def to_dict(self):
            return {"sampling": {"rate": 7}}

    sampler = sampler_from_config(FakeConfig())
    assert sampler.rate == 7


def test_sampler_from_config_no_to_dict():
    sampler = sampler_from_config(object())
    assert sampler.rate == 1
