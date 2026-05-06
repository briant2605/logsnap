"""Fluent builder for constructing a Pipeline from a LogSnapConfig."""
from __future__ import annotations

import sys
from typing import IO, Optional

from logsnap.aggregator import LogAggregator
from logsnap.config import LogSnapConfig
from logsnap.filter import LineFilter
from logsnap.metrics import MetricsCollector
from logsnap.output import PlainFormatter, JsonFormatter
from logsnap.pipeline import Pipeline
from logsnap.throttle import ThrottleManager


class PipelineBuilder:
    """Construct a ready-to-start Pipeline from a LogSnapConfig."""

    def __init__(self, config: LogSnapConfig) -> None:
        self._config = config
        self._stream: IO = sys.stdout

    def with_stream(self, stream: IO) -> "PipelineBuilder":
        self._stream = stream
        return self

    def build(self) -> Pipeline:
        cfg = self._config

        # Aggregator
        aggregator = LogAggregator(
            paths=cfg.sources,
            poll_interval=cfg.poll_interval,
        )

        # Filter
        line_filter = LineFilter(
            include=cfg.include_patterns,
            exclude=cfg.exclude_patterns,
        )

        # Throttle – one bucket per source using global rate if present
        rate_map = {src: cfg.max_lines_per_second for src in cfg.sources}
        throttle = ThrottleManager(rate_map)

        # Metrics
        metrics = MetricsCollector()

        # Formatter
        if cfg.output_format == "json":
            formatter = JsonFormatter()
        else:
            formatter = PlainFormatter(use_color=cfg.use_color)

        return Pipeline(
            aggregator=aggregator,
            line_filter=line_filter,
            throttle=throttle,
            metrics=metrics,
            formatter=formatter,
            output_stream=self._stream,
        )


def build_pipeline_from_config(config: LogSnapConfig, stream=None) -> Pipeline:
    """Convenience wrapper used by the CLI."""
    builder = PipelineBuilder(config)
    if stream is not None:
        builder.with_stream(stream)
    return builder.build()
