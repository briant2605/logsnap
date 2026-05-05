"""Tests for logsnap.filter.LineFilter."""

import pytest

from logsnap.filter import LineFilter


def test_no_patterns_accepts_all():
    f = LineFilter()
    lines = ["INFO hello", "ERROR boom", "DEBUG trace"]
    assert list(f.apply(lines)) == lines


def test_include_pattern_filters():
    f = LineFilter(include=["ERROR"])
    lines = ["INFO hello", "ERROR boom", "WARNING careful"]
    assert list(f.apply(lines)) == ["ERROR boom"]


def test_exclude_pattern_filters():
    f = LineFilter(exclude=["DEBUG"])
    lines = ["INFO hello", "DEBUG trace", "ERROR boom"]
    assert list(f.apply(lines)) == ["INFO hello", "ERROR boom"]


def test_include_and_exclude_combined():
    f = LineFilter(include=["user"], exclude=["admin"])
    lines = ["user login", "admin user action", "user logout", "system reboot"]
    assert list(f.apply(lines)) == ["user login", "user logout"]


def test_multiple_include_patterns_all_must_match():
    f = LineFilter(include=["ERROR", "database"])
    lines = ["ERROR something", "ERROR database connection failed", "database ok"]
    assert list(f.apply(lines)) == ["ERROR database connection failed"]


def test_case_insensitive():
    f = LineFilter(include=["error"], case_sensitive=False)
    lines = ["ERROR big problem", "info ok", "Error minor"]
    assert list(f.apply(lines)) == ["ERROR big problem", "Error minor"]


def test_matches_returns_bool():
    f = LineFilter(include=["OK"])
    assert f.matches("status OK") is True
    assert f.matches("status FAIL") is False


def test_repr_contains_patterns():
    f = LineFilter(include=["foo"], exclude=["bar"])
    r = repr(f)
    assert "foo" in r
    assert "bar" in r
