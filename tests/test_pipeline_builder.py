"""Tests for PipelineBuilder / build_pipeline_from_config."""
from __future__ import annotations

import io
from unittest.mock import patch, MagicMock

import pytest

from logsnap.config import LogSnapConfig
from logsnap.output import PlainFormatter, JsonFormatter
from logsnap.pipeline import Pipeline
from logsnap.pipeline_builder import PipelineBuilder, build_pipeline_from_config


def _cfg(**kwargs) -> LogSnapConfig:
    defaults = dict(
        sources=["/var/log/app.log"],
        include_patterns=[],
        exclude_patterns=[],
        poll_interval=0.5,
        max_lines_per_second=0,
        output_format="plain",
        use_color=False,
    )
    defaults.update(kwargs)
    return LogSnapConfig.from_dict(defaults)


@patch("logsnap.pipeline_builder.LogAggregator")
def test_builder_returns_pipeline(MockAgg):
    MockAgg.return_value = MagicMock()
    cfg = _cfg()
    p = PipelineBuilder(cfg).build()
    assert isinstance(p, Pipeline)


@patch("logsnap.pipeline_builder.LogAggregator")
def test_builder_uses_plain_formatter_by_default(MockAgg):
    MockAgg.return_value = MagicMock()
    cfg = _cfg(output_format="plain")
    p = PipelineBuilder(cfg).build()
    assert isinstance(p._formatter, PlainFormatter)


@patch("logsnap.pipeline_builder.LogAggregator")
def test_builder_uses_json_formatter(MockAgg):
    MockAgg.return_value = MagicMock()
    cfg = _cfg(output_format="json")
    p = PipelineBuilder(cfg).build()
    assert isinstance(p._formatter, JsonFormatter)


@patch("logsnap.pipeline_builder.LogAggregator")
def test_builder_passes_stream(MockAgg):
    MockAgg.return_value = MagicMock()
    buf = io.StringIO()
    cfg = _cfg()
    p = PipelineBuilder(cfg).with_stream(buf).build()
    assert p._stream is buf


@patch("logsnap.pipeline_builder.LogAggregator")
def test_convenience_wrapper(MockAgg):
    MockAgg.return_value = MagicMock()
    buf = io.StringIO()
    cfg = _cfg()
    p = build_pipeline_from_config(cfg, stream=buf)
    assert isinstance(p, Pipeline)
    assert p._stream is buf
