"""Tests for logsnap.watchdog."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Tuple

import pytest

from logsnap.watchdog import FileWatchdog, FileState, WatchdogEvent


@pytest.fixture()
def tmp(tmp_path: Path):
    return tmp_path


def _watchdog(path: str) -> Tuple[FileWatchdog, List[Tuple[str, str]]]:
    events: List[Tuple[str, str]] = []
    wd = FileWatchdog(path=path, on_event=lambda e, p: events.append((e, p)), poll_interval=0)
    return wd, events


def test_file_state_to_dict():
    fs = FileState(inode=42, size=100)
    assert fs.to_dict() == {"inode": 42, "size": 100}


def test_check_missing_file_returns_unchanged(tmp: Path):
    wd, events = _watchdog(str(tmp / "missing.log"))
    result = wd.check()
    assert result == WatchdogEvent.UNCHANGED
    assert events == []


def test_check_first_stat_returns_unchanged(tmp: Path):
    p = tmp / "app.log"
    p.write_text("hello\n")
    wd, events = _watchdog(str(p))
    result = wd.check()
    assert result == WatchdogEvent.UNCHANGED
    assert events == []


def test_check_file_grew(tmp: Path):
    p = tmp / "app.log"
    p.write_text("hello\n")
    wd, events = _watchdog(str(p))
    wd.check()  # seed state
    p.write_text("hello\nworld\n")
    result = wd.check()
    assert result == WatchdogEvent.GREW
    assert events == []


def test_check_file_unchanged(tmp: Path):
    p = tmp / "app.log"
    p.write_text("hello\n")
    wd, events = _watchdog(str(p))
    wd.check()
    result = wd.check()
    assert result == WatchdogEvent.UNCHANGED
    assert events == []


def test_check_detects_truncation(tmp: Path):
    p = tmp / "app.log"
    p.write_text("hello\nworld\n")
    wd, events = _watchdog(str(p))
    wd.check()  # seed
    p.write_text("")  # truncate
    result = wd.check()
    assert result == WatchdogEvent.TRUNCATED
    assert events == [(WatchdogEvent.TRUNCATED, str(p))]


def test_check_detects_rotation(tmp: Path):
    p = tmp / "app.log"
    p.write_text("original\n")
    wd, events = _watchdog(str(p))
    wd.check()  # seed
    # Simulate rotation: remove and recreate (new inode)
    p.unlink()
    p.write_text("new file\n")
    result = wd.check()
    assert result == WatchdogEvent.ROTATED
    assert events == [(WatchdogEvent.ROTATED, str(p))]


def test_start_limited_iterations(tmp: Path):
    p = tmp / "app.log"
    p.write_text("data\n")
    wd, events = _watchdog(str(p))
    wd.start(iterations=3)  # should not hang
    assert not wd._running  # loop exited


def test_stop_prevents_further_polling(tmp: Path):
    p = tmp / "app.log"
    p.write_text("data\n")
    wd, _ = _watchdog(str(p))
    wd._running = True
    wd.stop()
    assert not wd._running
