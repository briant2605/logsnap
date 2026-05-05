"""Tests for logsnap.checkpoint.CheckpointManager."""
import os
import time
import threading
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from logsnap.snapshot import SnapshotStore
from logsnap.checkpoint import CheckpointManager


def _make_tailer(path: str, inode: int, offset: int):
    tailer = MagicMock()
    tailer.path = path
    fh = MagicMock()
    fh.tell.return_value = offset
    tailer._fh = fh
    return tailer, inode


def test_record_saves_positions(tmp_path):
    snap_file = tmp_path / "snap.json"
    store = SnapshotStore(str(snap_file))
    tailer, inode = _make_tailer("/var/log/app.log", 7, 128)

    with patch("os.stat") as mock_stat:
        mock_stat.return_value.st_ino = inode
        mgr = CheckpointManager(store, [tailer])
        mgr.record()

    pos = store.get("/var/log/app.log")
    assert pos is not None
    assert pos.offset == 128
    assert pos.inode == 7


def test_restore_seeks_tailer(tmp_path):
    snap_file = tmp_path / "snap.json"
    store = SnapshotStore(str(snap_file))
    store.update("/var/log/app.log", inode=3, offset=512)
    store.save()

    tailer, _ = _make_tailer("/var/log/app.log", 3, 0)

    with patch("os.stat") as mock_stat:
        mock_stat.return_value.st_ino = 3
        mgr = CheckpointManager(store, [tailer])
        mgr.restore()

    tailer._fh.seek.assert_called_once_with(512)


def test_restore_skips_inode_mismatch(tmp_path):
    snap_file = tmp_path / "snap.json"
    store = SnapshotStore(str(snap_file))
    store.update("/var/log/app.log", inode=3, offset=512)

    tailer, _ = _make_tailer("/var/log/app.log", 99, 0)

    with patch("os.stat") as mock_stat:
        mock_stat.return_value.st_ino = 99
        mgr = CheckpointManager(store, [tailer])
        mgr.restore()

    tailer._fh.seek.assert_not_called()


def test_start_stop_calls_record(tmp_path):
    snap_file = tmp_path / "snap.json"
    store = SnapshotStore(str(snap_file))
    tailer, inode = _make_tailer("/var/log/app.log", 1, 0)

    with patch("os.stat") as mock_stat:
        mock_stat.return_value.st_ino = inode
        mgr = CheckpointManager(store, [tailer], interval=0.05)
        mgr.start()
        time.sleep(0.12)
        mgr.stop()

    # record() should have been called at least twice during the interval
    assert tailer._fh.tell.call_count >= 2
