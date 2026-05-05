"""Command-line entry point for logsnap."""

from __future__ import annotations

import argparse
import signal
import sys

from logsnap.aggregator import LogAggregator
from logsnap.filter import LineFilter
from logsnap.output import JsonFormatter, PlainFormatter


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="logsnap",
        description="Tail multiple log files and filter by pattern in real time.",
    )
    p.add_argument("files", nargs="+", metavar="FILE", help="Log files to tail")
    p.add_argument(
        "-i",
        "--include",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Include only lines matching PATTERN (may be repeated; all must match)",
    )
    p.add_argument(
        "-e",
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Exclude lines matching PATTERN (may be repeated)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Output events as newline-delimited JSON",
    )
    p.add_argument(
        "--color",
        action="store_true",
        help="Colorize source labels in plain output",
    )
    p.add_argument(
        "--interval",
        type=float,
        default=0.1,
        metavar="SECS",
        help="Poll interval in seconds (default: 0.1)",
    )
    return p


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    args = build_parser().parse_args(argv)

    line_filter = LineFilter(
        include_patterns=args.include,
        exclude_patterns=args.exclude,
    )

    aggregator = LogAggregator(
        paths=args.files,
        line_filter=line_filter,
        poll_interval=args.interval,
    )

    formatter = (
        JsonFormatter()
        if args.json
        else PlainFormatter(colorize=args.color)
    )

    def _shutdown(sig, frame):  # noqa: ANN001
        aggregator.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    aggregator.start()
    try:
        formatter.emit(aggregator.events())
    finally:
        aggregator.stop()


if __name__ == "__main__":  # pragma: no cover
    main()
