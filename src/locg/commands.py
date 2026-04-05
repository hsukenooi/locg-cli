"""Command implementations for locg CLI."""
from __future__ import annotations

import getpass
from datetime import date, timedelta
from typing import Any, Optional

from locg.client import LOCGClient
from locg.models import extract_comic_detail, extract_issue, extract_series
from locg.parser import parse_list_response, parse_page

# List ID mapping for add/remove operations
LIST_IDS = {
    "pull": 1,
    "collection": 2,
    "wish": 3,
    "read": 5,
}

VALID_LISTS = list(LIST_IDS.keys())


def _get_week_date(target: Optional[str] = None) -> str:
    """Return the date formatted as M/D/YYYY for LOCG API.

    If target is given (YYYY-MM-DD), use that date.
    Otherwise, find the most recent Wednesday (LOCG release day).
    """
    if target:
        parts = target.split("-")
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        return f"{m}/{d}/{y}"

    today = date.today()
    # Find the most recent Wednesday (weekday 2)
    days_since_wed = (today.weekday() - 2) % 7
    wed = today - timedelta(days=days_since_wed)
    return f"{wed.month}/{wed.day}/{wed.year}"


def cmd_search(client: LOCGClient, query: str) -> list[dict[str, Any]]:
    """Search for comic series by title."""
    resp = client.get("/comic/get_comics", params={
        "list": "search",
        "list_option": "series",
        "view": "thumbs",
        "title": query,
        "order": "alpha-asc",
    })
    count, soup = parse_list_response(resp.text)
    items = soup.find_all("li")
    return [extract_series(li) for li in items]


def cmd_releases(client: LOCGClient, target_date: Optional[str] = None) -> list[dict[str, Any]]:
    """Get new releases for a given week."""
    week_date = _get_week_date(target_date)
    resp = client.get("/comic/get_comics", params={
        "list": "releases",
        "view": "thumbs",
        "date_type": "week",
        "date": week_date,
        "order": "pulls",
    })
    count, soup = parse_list_response(resp.text)
    items = soup.find_all("li", class_="issue")
    return [extract_issue(li) for li in items]


def cmd_comic(client: LOCGClient, comic_id: int) -> dict[str, Any]:
    """Get full details for a specific comic."""
    resp = client.get(f"/comic/{comic_id}/x")
    if resp.status_code == 404:
        return {"error": f"Comic {comic_id} not found"}
    soup = parse_page(resp.text)
    return extract_comic_detail(soup)


def cmd_series(client: LOCGClient, series_id: int) -> dict[str, Any]:
    """Get series info and issue list."""
    resp = client.get("/comic/get_comics", params={
        "list": "search",
        "view": "thumbs",
        "format[]": "1",
        "series_id": str(series_id),
        "order": "date-desc",
    })
    count, soup = parse_list_response(resp.text)
    items = soup.find_all("li", class_="issue")
    issues = [extract_issue(li) for li in items]

    # If no issue-class items, try generic li (series search format)
    if not issues:
        items = soup.find_all("li")
        issues = [extract_issue(li) for li in items]

    return {
        "series_id": series_id,
        "issue_count": count,
        "issues": issues,
    }


def _get_user_list(client: LOCGClient, list_name: str, order: str = "alpha-asc") -> list[dict[str, Any]]:
    """Fetch a user's list (collection, pull, wish, read)."""
    client.require_auth()
    resp = client.get("/comic/get_comics", params={
        "list": list_name,
        "view": "thumbs",
        "order": order,
    })
    count, soup = parse_list_response(resp.text)
    items = soup.find_all("li", class_="issue")
    return [extract_issue(li) for li in items]


def cmd_collection(client: LOCGClient) -> list[dict[str, Any]]:
    """Get the user's collection."""
    return _get_user_list(client, "collection")


def cmd_pull_list(client: LOCGClient) -> list[dict[str, Any]]:
    """Get the user's pull list."""
    return _get_user_list(client, "pull", order="date-asc")


def cmd_wish_list(client: LOCGClient) -> list[dict[str, Any]]:
    """Get the user's wish list."""
    return _get_user_list(client, "wish")


def cmd_read_list(client: LOCGClient) -> list[dict[str, Any]]:
    """Get the user's read list."""
    return _get_user_list(client, "read")


def cmd_add(client: LOCGClient, list_name: str, comic_id: int) -> dict[str, Any]:
    """Add a comic to a list."""
    client.require_auth()
    if list_name not in LIST_IDS:
        return {"error": f"Invalid list '{list_name}'. Valid lists: {', '.join(VALID_LISTS)}"}
    resp = client.post("/comic/my_list_move", data={
        "comic_id": comic_id,
        "list_id": LIST_IDS[list_name],
        "action_id": 1,
    })
    try:
        return resp.json()
    except Exception:
        return {"status": "ok" if resp.status_code == 200 else "error"}


def cmd_remove(client: LOCGClient, list_name: str, comic_id: int) -> dict[str, Any]:
    """Remove a comic from a list."""
    client.require_auth()
    if list_name not in LIST_IDS:
        return {"error": f"Invalid list '{list_name}'. Valid lists: {', '.join(VALID_LISTS)}"}
    resp = client.post("/comic/my_list_move", data={
        "comic_id": comic_id,
        "list_id": LIST_IDS[list_name],
        "action_id": 0,
    })
    try:
        return resp.json()
    except Exception:
        return {"status": "ok" if resp.status_code == 200 else "error"}


def cmd_login(client: LOCGClient, username: Optional[str] = None, password: Optional[str] = None) -> dict[str, Any]:
    """Log in to LOCG. Prompts for credentials if not provided."""
    if not username:
        username = input("Username: ")
    if not password:
        password = getpass.getpass("Password: ")
    success = client.login(username, password)
    if success:
        return {"status": "ok", "username": username}
    return {"error": "Login failed. Check your username and password."}
