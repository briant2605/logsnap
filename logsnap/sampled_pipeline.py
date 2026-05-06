"""Pipeline wrapper that applies LineSampler before emitting events."""
from __future__ import annotations

from typing import Optional

from logsnap.pipeline import Pipeline
from logsnap.sampling import LineSampler
from logsnap.aggregator import LogEvent


class SampledPipeline:
    """Wraps a :class:`Pipeline` and gates events through a :class:`LineSampler`.

    This keeps all existing pipeline logic (filtering, metrics, throttle,
    dedup, alerting) intact while adding a sampling layer on top.
    """

    def __init__(self, pipeline: Pipeline, sampler: LineSampler) -> None:
        self._pipeline = pipeline
        self._sampler = sampler

    # ------------------------------------------------------------------
    # Delegation helpers

    def start(self) -> None:
        self._pipeline.start()

    def stop(self) -> None:
        self._pipeline.stop()

    def join(self, timeout: Optional[float] = None) -> None:
        self._pipeline.join(timeout)

    # ------------------------------------------------------------------
    # Core sampling logic

    def process_event(self, event: LogEvent) -> bool:
        """Process *event* through sampler then pipeline.

        Returns True if the event was forwarded to the inner pipeline,
        False if it was dropped by the sampler.
        """
        if not self._sampler.should_emit(event.source):
            return False
        self._pipeline._process_event(event)  # noqa: SLF001
        return True

    @property
    def sampler(self) -> LineSampler:
        return self._sampler

    @property
    def pipeline(self) -> Pipeline:
        return self._pipeline

    def __repr__(self) -> str:  # pragma: no cover
        return f"SampledPipeline(sampler={self._sampler!r}, pipeline={self._pipeline!r})"
