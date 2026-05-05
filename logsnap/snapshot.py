"""Snapshot: capture and persist the current state of tailed log positions."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional


@dataclass
class FilePosition:
    path: str
    inode: int
    offset: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FilePosition":
        return cls(**data)


class SnapshotStore:
    """Persist and restore file tail positions across restarts."""

    def __init__(self, snapshot_path: str) -> None:
        self._path = Path(snapshot_path)
        self._positions: Dict[str, FilePosition] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text())
            self._positions = {
                k: FilePosition.from_dict(v) for k, v in raw.items()
            }
        except (json.JSONDecodeError, KeyError, TypeError):
            self._positions = {}

    def get(self, file_path: str) -> Optional[FilePosition]:
        return self._positions.get(file_path)

    def update(self, file_path: str, inode: int, offset: int) -> None:
        self._positions[file_path] = FilePosition(
            path=file_path, inode=inode, offset=offset
        )

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(
                {k: v.to_dict() for k, v in self._positions.items()},
                indent=2,
            )
        )
        tmp.replace(self._path)

    def remove(self, file_path: str) -> None:
        self._positions.pop(file_path, None)

    def all(self) -> Dict[str, FilePosition]:
        return dict(self._positions)
