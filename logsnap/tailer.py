"""Core log file tailer that watches a file and yields new lines in real time."""

import os
import time
from typing import Generator, Optional


class LogTailer:
    """Tails a single log file, yielding new lines as they are written."""

    def __init__(self, filepath: str, poll_interval: float = 0.1) -> None:
        self.filepath = filepath
        self.poll_interval = poll_interval
        self._file = None
        self._inode: Optional[int] = None

    def _open(self) -> None:
        self._file = open(self.filepath, "r", encoding="utf-8", errors="replace")
        self._file.seek(0, os.SEEK_END)
        self._inode = os.fstat(self._file.fileno()).st_ino

    def _rotated(self) -> bool:
        """Return True if the file has been rotated (inode changed or missing)."""
        try:
            return os.stat(self.filepath).st_ino != self._inode
        except FileNotFoundError:
            return True

    def tail(self) -> Generator[str, None, None]:
        """Yield new lines from the file indefinitely."""
        while not os.path.exists(self.filepath):
            time.sleep(self.poll_interval)

        self._open()
        try:
            while True:
                line = self._file.readline()
                if line:
                    yield line.rstrip("\n")
                else:
                    if self._rotated():
                        self._file.close()
                        self._open()
                    else:
                        time.sleep(self.poll_interval)
        finally:
            if self._file:
                self._file.close()

    def __repr__(self) -> str:
        return f"LogTailer(filepath={self.filepath!r}, poll_interval={self.poll_interval})"
