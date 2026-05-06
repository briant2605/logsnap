"""Checkpoint manager: integrates SnapshotStore with LogTailer instances."""
from __future__ import annotations

import os
import threading
from typing import Dict, List

from logsnap.snapshot import SnapshotStore
from logsnap.tailer import LogTailer


class CheckpointManager:
    """Periodically saves tailer positions and restores them on startup."""

    def __init__(
        self,
        store: SnapshotStore,
        tailers: List[LogTailer],
        interval: float = 5.0,
    ) -> None:
        self._store = store
        self._tailers: Dict[str, LogTailer] = {t.path: t for t in tailers}
        self._interval = interval
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._stopped = False

    def restore(self) -> None:
        """Seek each tailer to its last known position if inode matches."""
        for path, tailer in self._tailers.items():
            pos = self._store.get(path)
            if pos is None:
                continue
            try:
                inode = os.stat(path).st_ino
            except FileNotFoundError:
                continue
            if inode == pos.inode and tailer._fh is not None:
                tailer._fh.seek(pos.offset)

    def record(self) -> None:
        """Capture current offsets from all tailers into the store."""
        with self._lock:
            for path, tailer in self._tailers.items():
                if tailer._fh is None:
                    continue
                try:
                    inode = os.stat(path).st_ino
                    offset = tailer._fh.tell()
                    self._store.update(path, inode, offset)
                except OSError:
                    pass
            self._store.save()

    def add_tailer(self, tailer: LogTailer) -> None:
        """Register a new tailer with the manager at runtime.

        If a checkpoint already exists for the tailer's path and the inode
        matches, the tailer is immediately seeked to its last known offset.
        """
        with self._lock:
            self._tailers[tailer.path] = tailer
        # Attempt to restore position for the newly added tailer.
        pos = self._store.get(tailer.path)
        if pos is None or tailer._fh is None:
            return
        try:
            inode = os.stat(tailer.path).st_ino
        except FileNotFoundError:
            return
        if inode == pos.inode:
            tailer._fh.seek(pos.offset)

    def _schedule(self) -> None:
        if self._stopped:
            return
        self.record()
        self._timer = threading.Timer(self._interval, self._schedule)
        self._timer.daemon = True
        self._timer.start()

    def start(self) -> None:
        self._stopped = False
        self._schedule()

    def stop(self) -> None:
        self._stopped = True
        if self._timer:
            self._timer.cancel()
        self.record()
