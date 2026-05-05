"""Configuration loader for logsnap (TOML/JSON with snapshot support)."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


@dataclass
class LogSnapConfig:
    files: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    output_format: str = "plain"  # plain | json
    color: bool = True
    snapshot_path: Optional[str] = None
    snapshot_interval: float = 5.0
    poll_interval: float = 0.1

    @classmethod
    def from_dict(cls, data: dict) -> "LogSnapConfig":
        allowed = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in allowed}
        return cls(**filtered)

    @classmethod
    def load(cls, path: str) -> "LogSnapConfig":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        suffix = p.suffix.lower()
        if suffix == ".json":
            data = json.loads(p.read_text())
        elif suffix == ".toml":
            if tomllib is None:
                raise RuntimeError(
                    "tomllib is not available; use Python 3.11+ or install tomli."
                )
            with open(p, "rb") as fh:
                data = tomllib.load(fh)
        else:
            raise ValueError(f"Unsupported config format: {suffix}")
        return cls.from_dict(data)

    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self)
