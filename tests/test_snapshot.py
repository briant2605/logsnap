"""Tests for logsnap.snapshot.SnapshotStore."""
import json
import pytest
from pathlib import Path

from logsnap.snapshot import FilePosition, SnapshotStore


def test_fileposition_roundtrip():
    fp = FilePosition(path="/var/log/app.log", inode=1234, offset=512)
    assert FilePosition.from_dict(fp.to_dict()) == fp


def test_store_empty_on_missing_file(tmp_path):
    store = SnapshotStore(str(tmp_path / "snap.json"))
    assert store.get("/some/file") is None


def test_store_update_and_get(tmp_path):
    store = SnapshotStore(str(tmp_path / "snap.json"))
    store.update("/var/log/app.log", inode=99, offset=256)
    pos = store.get("/var/log/app.log")
    assert pos is not None
    assert pos.inode == 99
    assert pos.offset == 256


def test_store_save_and_reload(tmp_path):
    snap_file = tmp_path / "snap.json"
    store = SnapshotStore(str(snap_file))
    store.update("/var/log/a.log", inode=1, offset=100)
    store.update("/var/log/b.log", inode=2, offset=200)
    store.save()

    store2 = SnapshotStore(str(snap_file))
    assert store2.get("/var/log/a.log").offset == 100
    assert store2.get("/var/log/b.log").inode == 2


def test_store_remove(tmp_path):
    store = SnapshotStore(str(tmp_path / "snap.json"))
    store.update("/var/log/app.log", inode=1, offset=0)
    store.remove("/var/log/app.log")
    assert store.get("/var/log/app.log") is None


def test_store_tolerates_corrupt_file(tmp_path):
    snap_file = tmp_path / "snap.json"
    snap_file.write_text("not valid json{{")
    store = SnapshotStore(str(snap_file))
    assert store.all() == {}


def test_store_save_is_atomic(tmp_path):
    snap_file = tmp_path / "snap.json"
    store = SnapshotStore(str(snap_file))
    store.update("/var/log/app.log", inode=5, offset=42)
    store.save()
    # No .tmp file should linger
    assert not (tmp_path / "snap.tmp").exists()
    data = json.loads(snap_file.read_text())
    assert "/var/log/app.log" in data
