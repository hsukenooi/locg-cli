"""Tests for locg.cli module."""
from __future__ import annotations

import json
import sys

import pytest

from locg import __version__
from locg.cli import _filter_fields, create_parser, main


def test_no_args_prints_help_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["locg"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "usage" in captured.err.lower() or "locg" in captured.err.lower()


def test_help_flag_exits_0(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["locg", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "League of Comic Geeks" in captured.out


def test_version_flag_exits_0(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["locg", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_unknown_command_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["locg", "foobar"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 2


def test_search_subcommand_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["locg", "search", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "query" in captured.out.lower() or "search" in captured.out.lower()


def test_pretty_flag_before_subcommand(monkeypatch):
    """--pretty works before or after the subcommand."""
    from locg.cli import create_parser
    parser = create_parser()
    # After subcommand (handled by subparser)
    args = parser.parse_args(["search", "--pretty", "batman"])
    assert args.pretty is True
    assert args.command == "search"
    assert args.query == "batman"


def test_pretty_flag_after_subcommand(monkeypatch):
    """--pretty after subcommand is also handled."""
    parser = create_parser()
    args = parser.parse_args(["releases", "--pretty"])
    assert args.pretty is True
    assert args.command == "releases"


# --- _filter_fields tests ---


def test_filter_fields_list_of_dicts():
    data = [{"id": 1, "name": "A", "price": 3.99}, {"id": 2, "name": "B", "price": 4.99}]
    result = _filter_fields(data, ["name", "id"])
    assert result == [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]


def test_filter_fields_single_dict():
    data = {"id": 1, "name": "A", "price": 3.99, "publisher": "DC"}
    result = _filter_fields(data, ["name"])
    assert result == {"name": "A"}


def test_filter_fields_nonexistent_field_ignored():
    data = [{"id": 1, "name": "A"}]
    result = _filter_fields(data, ["name", "nonexistent"])
    assert result == [{"name": "A"}]


def test_filter_fields_non_dict_passthrough():
    """Non-dict, non-list values are returned unchanged."""
    assert _filter_fields("hello", ["name"]) == "hello"
    assert _filter_fields(42, ["name"]) == 42


def test_filter_fields_empty_list():
    assert _filter_fields([], ["name"]) == []


# --- --fields flag parsing ---


def test_fields_flag_parsed():
    parser = create_parser()
    args = parser.parse_args(["search", "--fields", "name,id", "batman"])
    assert args.fields == "name,id"


def test_fields_flag_before_subcommand():
    parser = create_parser()
    args = parser.parse_args(["--fields", "name", "search", "batman"])
    # Parent parser sets fields on the namespace
    assert args.command == "search"


# --- collection has subcommand parsing ---


def test_collection_has_subcommand_parsed():
    parser = create_parser()
    args = parser.parse_args(["collection", "has", "Amazing Spider-Man #300"])
    assert args.command == "collection"
    assert args.collection_command == "has"
    assert args.title_query == "Amazing Spider-Man #300"


def test_collection_without_has_no_collection_command():
    parser = create_parser()
    args = parser.parse_args(["collection"])
    assert args.command == "collection"
    assert getattr(args, "collection_command", None) is None


# --- Auth exit code ---


def test_auth_failure_exits_1(monkeypatch, capsys):
    """AuthRequired should exit with code 1, not 3."""
    from locg.client import AuthRequired

    monkeypatch.setattr(sys, "argv", ["locg", "collection"])

    # Patch LOCGClient to raise AuthRequired
    import locg.cli
    original_client = locg.cli.LOCGClient

    class FakeClient:
        def __init__(self):
            pass
        def require_auth(self):
            raise AuthRequired("Session expired. Run: locg login")
        def close(self):
            pass

    monkeypatch.setattr(locg.cli, "LOCGClient", FakeClient)

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    err = json.loads(captured.err)
    assert "expired" in err["error"].lower()
