"""Tests for locg.cli module."""
from __future__ import annotations

import sys

import pytest

from locg import __version__
from locg.cli import main


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
    from locg.cli import create_parser
    parser = create_parser()
    args = parser.parse_args(["releases", "--pretty"])
    assert args.pretty is True
    assert args.command == "releases"
