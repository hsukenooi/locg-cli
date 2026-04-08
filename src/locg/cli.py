"""CLI entry point for locg."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from locg import __version__
from locg.client import AuthRequired, LOCGClient
from locg.commands import (
    VALID_LISTS,
    cmd_add,
    cmd_check_lists,
    cmd_collection,
    cmd_comic,
    cmd_login,
    cmd_pull_list,
    cmd_read_list,
    cmd_releases,
    cmd_remove,
    cmd_search,
    cmd_series,
    cmd_wish_list,
)


def die(msg: str, code: int = 1) -> None:
    """Print structured JSON error to stderr and exit."""
    json.dump({"error": msg}, sys.stderr)
    print(file=sys.stderr)
    sys.exit(code)


def output(data: Any, pretty: bool = False) -> None:
    """Print JSON data to stdout."""
    if pretty:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(data, separators=(",", ":"), ensure_ascii=False))


def create_parser() -> argparse.ArgumentParser:
    # Shared flags available on all subcommands
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    common.add_argument("-v", "--verbose", action="store_true", help="Verbose output (INFO level)")
    common.add_argument("--debug", action="store_true", help="Debug output (DEBUG level, includes HTTP details)")

    parser = argparse.ArgumentParser(
        prog="locg",
        description="CLI for League of Comic Geeks",
        parents=[common],
    )
    parser.add_argument("--version", action="version", version=f"locg {__version__}")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # search
    p = sub.add_parser("search", parents=[common], help="Search for comic series")
    p.add_argument("query", help="Search term")

    # releases
    p = sub.add_parser("releases", parents=[common], help="New releases for a given week")
    p.add_argument("--date", help="Week date (YYYY-MM-DD), default: this week")

    # comic
    p = sub.add_parser("comic", parents=[common], help="Get comic details")
    p.add_argument("id", type=int, help="Comic ID")

    # series
    p = sub.add_parser("series", parents=[common], help="Get series details and issue list")
    p.add_argument("id", type=int, help="Series ID")

    # collection
    p = sub.add_parser("collection", parents=[common], help="View your collection (requires login)")
    p.add_argument("--title", help="Filter results by title (case-insensitive substring match)")

    # pull-list
    p = sub.add_parser("pull-list", parents=[common], help="View your pull list (requires login)")
    p.add_argument("--title", help="Filter results by title (case-insensitive substring match)")

    # wish-list
    p = sub.add_parser("wish-list", parents=[common], help="View your wish list (requires login)")
    p.add_argument("--title", help="Filter results by title (case-insensitive substring match)")

    # read-list
    p = sub.add_parser("read-list", parents=[common], help="View your read list (requires login)")
    p.add_argument("--title", help="Filter results by title (case-insensitive substring match)")

    # add
    p = sub.add_parser("add", parents=[common], help="Add a comic to a list")
    p.add_argument("list", choices=VALID_LISTS, help="Target list")
    p.add_argument("comic_id", type=int, help="Comic ID")

    # remove
    p = sub.add_parser("remove", parents=[common], help="Remove a comic from a list")
    p.add_argument("list", choices=VALID_LISTS, help="Target list")
    p.add_argument("comic_id", type=int, help="Comic ID")

    # check
    p = sub.add_parser("check", parents=[common], help="Check which lists comics belong to (requires login)")
    p.add_argument("comic_ids", type=int, nargs="+", help="One or more comic IDs")

    # login
    p = sub.add_parser("login", parents=[common], help="Log in to League of Comic Geeks")
    p.add_argument("-u", "--username", help="Username (prompts if not provided)")
    p.add_argument("-p", "--password", help="Password (prompts if not provided)")

    return parser


def main() -> None:
    # Pre-scan for global flags before argparse, since parent parser
    # defaults can overwrite values when flags appear before subcommand
    raw = sys.argv[1:]
    pretty = "--pretty" in raw
    debug = "--debug" in raw
    verbose = "--verbose" in raw or "-v" in raw

    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help(sys.stderr)
        sys.exit(2)

    # Use pre-scanned values (handles both `locg --pretty releases` and `locg releases --pretty`)
    args.pretty = pretty
    args.debug = debug
    args.verbose = verbose

    # Configure logging to stderr (keeps stdout clean for JSON)
    if args.debug:
        level = logging.DEBUG
    elif args.verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    logger = logging.getLogger("locg")
    client = LOCGClient()

    try:
        result: Any = None
        logger.info(f"Running command: {args.command}")

        if args.command == "search":
            result = cmd_search(client, args.query)
        elif args.command == "releases":
            result = cmd_releases(client, args.date)
        elif args.command == "comic":
            result = cmd_comic(client, args.id)
        elif args.command == "series":
            result = cmd_series(client, args.id)
        elif args.command == "collection":
            result = cmd_collection(client, title=args.title)
        elif args.command == "pull-list":
            result = cmd_pull_list(client, title=args.title)
        elif args.command == "wish-list":
            result = cmd_wish_list(client, title=args.title)
        elif args.command == "read-list":
            result = cmd_read_list(client, title=args.title)
        elif args.command == "add":
            result = cmd_add(client, args.list, args.comic_id)
        elif args.command == "remove":
            result = cmd_remove(client, args.list, args.comic_id)
        elif args.command == "check":
            result = cmd_check_lists(client, args.comic_ids)
        elif args.command == "login":
            result = cmd_login(client, username=args.username, password=args.password)

        if result is not None:
            output(result, pretty=args.pretty)

    except AuthRequired as e:
        die(str(e), code=3)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        die(str(e), code=4)
    finally:
        client.close()
