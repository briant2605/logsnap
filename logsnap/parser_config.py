"""Load a LineParser from config dict / top-level config object."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from logsnap.parser import LineParser, ParseRule

# Built-in named patterns available as shortcuts in config
_BUILTINS: Dict[str, str] = {
    "common_log": (
        r'(?P<host>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
        r'"(?P<method>\S+) (?P<path>\S+) \S+" (?P<status>\d{3}) (?P<bytes>\d+|-)'
    ),
    "syslog": (
        r"(?P<month>\w{3})\s+(?P<day>\d+) (?P<time>\d{2}:\d{2}:\d{2}) "
        r"(?P<host>\S+) (?P<program>\S+?)(?:\[(?P<pid>\d+)\])?: (?P<message>.*)"
    ),
    "nginx_error": (
        r"(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2}) (?P<time>\d{2}:\d{2}:\d{2}) "
        r"\[(?P<level>\w+)\] (?P<message>.*)"
    ),
}


def _rule_from_dict(d: Dict[str, Any]) -> ParseRule:
    name = d.get("name", "unnamed")
    builtin = d.get("builtin")
    if builtin:
        raw_pattern = _BUILTINS.get(builtin)
        if raw_pattern is None:
            raise ValueError(f"Unknown built-in parser pattern: {builtin!r}")
    else:
        raw_pattern = d["pattern"]
    flags = re.IGNORECASE if d.get("ignore_case", False) else 0
    compiled = re.compile(raw_pattern, flags)
    defaults: Dict[str, str] = d.get("defaults", {})
    return ParseRule(name=name, pattern=compiled, defaults=defaults)


def parser_from_dict(rules_list: Optional[List[Dict[str, Any]]]) -> LineParser:
    parser = LineParser()
    if not rules_list:
        return parser
    for item in rules_list:
        parser.add_rule(_rule_from_dict(item))
    return parser


def parser_from_config(cfg: Any) -> LineParser:
    """Extract parser rules from a LogSnapConfig-like object."""
    raw = getattr(cfg, "parser", None)
    if raw is None:
        return LineParser()
    return parser_from_dict(raw)
