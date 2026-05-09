"""Tests for logsnap.parser_config."""
import pytest
from logsnap.parser_config import parser_from_dict, parser_from_config


# ---------------------------------------------------------------------------
# parser_from_dict
# ---------------------------------------------------------------------------

def test_none_returns_empty_parser():
    parser = parser_from_dict(None)
    assert parser.parse("anything") == {"raw": "anything"}


def test_empty_list_returns_empty_parser():
    parser = parser_from_dict([])
    assert parser.parse("x") == {"raw": "x"}


def test_custom_pattern_loaded():
    cfg = [{"name": "level_msg", "pattern": r"(?P<level>\w+) (?P<msg>.+)"}]
    parser = parser_from_dict(cfg)
    result = parser.parse("ERROR disk full")
    assert result["level"] == "ERROR"
    assert result["msg"] == "disk full"
    assert result["_rule"] == "level_msg"


def test_builtin_common_log():
    cfg = [{"name": "access", "builtin": "common_log"}]
    parser = parser_from_dict(cfg)
    line = '127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326'
    result = parser.parse(line)
    assert result["host"] == "127.0.0.1"
    assert result["status"] == "200"
    assert result["method"] == "GET"


def test_builtin_syslog():
    cfg = [{"name": "sys", "builtin": "syslog"}]
    parser = parser_from_dict(cfg)
    line = "Jan  5 12:00:00 myhost myapp[1234]: something happened"
    result = parser.parse(line)
    assert result["host"] == "myhost"
    assert result["program"] == "myapp"
    assert result["pid"] == "1234"


def test_unknown_builtin_raises():
    with pytest.raises(ValueError, match="Unknown built-in"):
        parser_from_dict([{"name": "x", "builtin": "nonexistent"}])


def test_ignore_case_flag():
    cfg = [{"name": "r", "pattern": r"(?P<level>error)", "ignore_case": True}]
    parser = parser_from_dict(cfg)
    result = parser.parse("ERROR something")
    assert result["level"] == "ERROR"


def test_defaults_merged():
    cfg = [{"name": "r", "pattern": r"(?P<msg>.+)", "defaults": {"env": "prod"}}]
    parser = parser_from_dict(cfg)
    result = parser.parse("hello")
    assert result["env"] == "prod"


# ---------------------------------------------------------------------------
# parser_from_config
# ---------------------------------------------------------------------------

def test_parser_from_config_no_attr():
    class Cfg:
        pass
    parser = parser_from_config(Cfg())
    assert parser.parse("x") == {"raw": "x"}


def test_parser_from_config_reads_parser_attr():
    class Cfg:
        parser = [{"name": "r", "pattern": r"(?P<word>\w+)"}]
    p = parser_from_config(Cfg())
    result = p.parse("hello world")
    assert result["word"] == "hello"
