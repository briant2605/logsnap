"""Tests for logsnap.tailer.LogTailer."""

import os
import tempfile
import threading
import time

import pytest

from logsnap.tailer import LogTailer


def _collect_lines(tailer: LogTailer, count: int, timeout: float = 3.0):
    """Collect *count* lines from *tailer.tail()* with a timeout."""
    results = []

    def _run():
        for line in tailer.tail():
            results.append(line)
            if len(results) >= count:
                break

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    return results


def test_tail_reads_new_lines():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        path = f.name

    try:
        tailer = LogTailer(filepath=path, poll_interval=0.05)

        def _write():
            time.sleep(0.1)
            with open(path, "a") as fh:
                fh.write("hello world\n")
                fh.write("second line\n")

        threading.Thread(target=_write, daemon=True).start()
        lines = _collect_lines(tailer, count=2)

        assert lines == ["hello world", "second line"]
    finally:
        os.unlink(path)


def test_tail_waits_for_file_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "new.log")
        tailer = LogTailer(filepath=path, poll_interval=0.05)

        def _create_and_write():
            time.sleep(0.15)
            with open(path, "w") as fh:
                fh.write("appeared\n")

        threading.Thread(target=_create_and_write, daemon=True).start()
        lines = _collect_lines(tailer, count=1)
        assert lines == ["appeared"]


def test_repr():
    t = LogTailer("/var/log/app.log")
    assert "LogTailer" in repr(t)
    assert "/var/log/app.log" in repr(t)
