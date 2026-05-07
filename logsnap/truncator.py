"""Line truncation for log events that exceed a maximum length."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

_DEFAULT_MAX_BYTES = 4096
_ELLIPSIS = "...[truncated]"


@dataclass
class TruncatorStats:
    total_lines: int = 0
    truncated_lines: int = 0
    bytes_dropped: int = 0

    def to_dict(self) -> dict:
        return {
            "total_lines": self.total_lines,
            "truncated_lines": self.truncated_lines,
            "bytes_dropped": self.bytes_dropped,
        }


class LineTruncator:
    """Truncates log lines that exceed *max_bytes* bytes (UTF-8 encoded).

    Args:
        max_bytes: Maximum allowed byte length for a line.  Lines longer than
            this are cut and suffixed with an ellipsis marker.  ``None`` or
            ``0`` disables truncation entirely.
        ellipsis: Suffix appended to truncated lines.
    """

    def __init__(
        self,
        max_bytes: Optional[int] = _DEFAULT_MAX_BYTES,
        ellipsis: str = _ELLIPSIS,
    ) -> None:
        if max_bytes is not None and max_bytes < 0:
            raise ValueError("max_bytes must be >= 0 or None")
        self._max_bytes = max_bytes or 0
        self._ellipsis = ellipsis
        self._stats: dict[str, TruncatorStats] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def truncate(self, line: str, source: str = "") -> str:
        """Return *line*, truncating it if it exceeds *max_bytes*."""
        stats = self._stats.setdefault(source, TruncatorStats())
        stats.total_lines += 1

        if not self._max_bytes:
            return line

        encoded = line.encode("utf-8")
        if len(encoded) <= self._max_bytes:
            return line

        suffix = self._ellipsis.encode("utf-8")
        keep = max(0, self._max_bytes - len(suffix))
        truncated = encoded[:keep].decode("utf-8", errors="ignore") + self._ellipsis

        stats.truncated_lines += 1
        stats.bytes_dropped += len(encoded) - self._max_bytes
        return truncated

    def stats(self, source: str = "") -> TruncatorStats:
        """Return cumulative stats for *source* (creates entry if absent)."""
        return self._stats.setdefault(source, TruncatorStats())

    def all_stats(self) -> dict[str, dict]:
        """Return stats for every source as plain dicts."""
        return {src: s.to_dict() for src, s in self._stats.items()}

    def reset(self, source: Optional[str] = None) -> None:
        """Reset stats for *source*, or all sources if *source* is ``None``."""
        if source is None:
            self._stats.clear()
        else:
            self._stats.pop(source, None)

    def __repr__(self) -> str:  # pragma: no cover
        return f"LineTruncator(max_bytes={self._max_bytes!r})"
