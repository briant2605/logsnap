"""Tests for logsnap.retry."""
import pytest

from logsnap.retry import RetryEmitter, RetryPolicy, RetryStats


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

def test_policy_delay_zero_for_first_attempt():
    p = RetryPolicy(base_delay=1.0)
    assert p.delay_for(0) == 0.0


def test_policy_delay_exponential_backoff():
    p = RetryPolicy(base_delay=1.0, backoff_factor=2.0, max_delay=100.0)
    assert p.delay_for(1) == 1.0
    assert p.delay_for(2) == 2.0
    assert p.delay_for(3) == 4.0


def test_policy_delay_capped_at_max():
    p = RetryPolicy(base_delay=1.0, backoff_factor=2.0, max_delay=3.0)
    assert p.delay_for(4) == 3.0


def test_policy_invalid_max_attempts_raises():
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)


def test_policy_invalid_base_delay_raises():
    with pytest.raises(ValueError):
        RetryPolicy(base_delay=-1.0)


def test_policy_invalid_backoff_factor_raises():
    with pytest.raises(ValueError):
        RetryPolicy(backoff_factor=0.5)


# ---------------------------------------------------------------------------
# RetryStats
# ---------------------------------------------------------------------------

def test_stats_to_dict_defaults():
    s = RetryStats()
    d = s.to_dict()
    assert d == {"attempts": 0, "successes": 0, "failures": 0, "dropped": 0}


# ---------------------------------------------------------------------------
# RetryEmitter — success path
# ---------------------------------------------------------------------------

def test_emit_succeeds_on_first_attempt():
    received: list[str] = []
    emitter = RetryEmitter(emit=received.append, sleep_fn=lambda _: None)
    result = emitter.emit("hello")
    assert result is True
    assert received == ["hello"]
    assert emitter.stats.attempts == 1
    assert emitter.stats.successes == 1
    assert emitter.stats.failures == 0


def test_emit_retries_on_transient_failure():
    calls: list[int] = []

    def flaky(line: str) -> None:
        calls.append(1)
        if len(calls) < 3:
            raise OSError("transient")

    emitter = RetryEmitter(
        emit=flaky,
        policy=RetryPolicy(max_attempts=3, base_delay=0.0),
        sleep_fn=lambda _: None,
    )
    result = emitter.emit("x")
    assert result is True
    assert emitter.stats.attempts == 3
    assert emitter.stats.successes == 1
    assert emitter.stats.failures == 0


def test_emit_drops_after_max_attempts():
    def always_fail(line: str) -> None:
        raise RuntimeError("boom")

    emitter = RetryEmitter(
        emit=always_fail,
        policy=RetryPolicy(max_attempts=2, base_delay=0.0),
        sleep_fn=lambda _: None,
    )
    result = emitter.emit("bad")
    assert result is False
    assert emitter.stats.attempts == 2
    assert emitter.stats.failures == 1
    assert emitter.stats.dropped == 1


def test_emit_sleeps_between_retries():
    sleeps: list[float] = []

    def fail_once(line: str) -> None:
        if not sleeps:
            raise OSError("first")

    emitter = RetryEmitter(
        emit=fail_once,
        policy=RetryPolicy(max_attempts=2, base_delay=1.0),
        sleep_fn=sleeps.append,
    )
    emitter.emit("msg")
    assert len(sleeps) == 1
    assert sleeps[0] == 1.0
