"""Periodic heartbeat emitter that logs a status line at a fixed interval."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class HeartbeatConfig:
    interval: float = 60.0          # seconds between heartbeats
    message: str = "[logsnap] heartbeat"
    source: str = "__heartbeat__"

    def __post_init__(self) -> None:
        if self.interval <= 0:
            raise ValueError(f"interval must be positive, got {self.interval}")


class HeartbeatEmitter:
    """Calls *callback* with a heartbeat message at a regular interval.

    The callback receives ``(source: str, line: str)``.
    """

    def __init__(
        self,
        config: HeartbeatConfig,
        callback: Callable[[str, str], None],
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cfg = config
        self._callback = callback
        self._clock = clock
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the background heartbeat thread."""
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="heartbeat", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the heartbeat thread to stop and wait for it."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    # ------------------------------------------------------------------
    def _run(self) -> None:
        interval = self._cfg.interval
        while not self._stop_event.wait(timeout=interval):
            self._emit()

    def _emit(self) -> None:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        line = f"{self._cfg.message} ts={ts}"
        self._callback(self._cfg.source, line)

    # ------------------------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"HeartbeatEmitter(interval={self._cfg.interval}, "
            f"source={self._cfg.source!r})"
        )


# ---------------------------------------------------------------------------
# Config helper
# ---------------------------------------------------------------------------

def heartbeat_from_dict(data: Optional[dict]) -> Optional[HeartbeatConfig]:
    """Build a :class:`HeartbeatConfig` from a config dict (or *None*)."""
    if not data:
        return None
    return HeartbeatConfig(
        interval=float(data.get("interval", 60.0)),
        message=str(data.get("message", "[logsnap] heartbeat")),
        source=str(data.get("source", "__heartbeat__")),
    )
