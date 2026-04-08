"""Tests for locg.commands module."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, call

from locg.client import AuthRequired
from locg.commands import (
    _PAGE_SIZE,
    _fetch_user_list_page,
    _filter_by_list_membership,
    _filter_by_title,
    _get_user_list,
    _get_week_date,
    cmd_add,
    cmd_check_lists,
    cmd_collection,
    cmd_pull_list,
    cmd_read_list,
    cmd_releases,
    cmd_remove,
    cmd_search,
    cmd_wish_list,
)


def _make_issue_html(comic_id: int, name: str = "Issue") -> str:
    """Build a minimal <li class='issue'> HTML snippet for testing."""
    return (
        f'<li class="issue" data-comic="{comic_id}" data-pulls="0" '
        f'data-potw="0" data-community="0">'
        f'<div class="title"><a href="/comic/{comic_id}/x">{name} #{comic_id}</a></div>'
        f'<div class="publisher">Test Pub</div>'
        f'</li>'
    )


def _make_issue_html_with_lists(
    comic_id: int,
    name: str = "Issue",
    active_lists: list[int] | None = None,
) -> str:
    """Build an <li class='issue'> with comic-controller spans for list membership.

    *active_lists* is a list of LOCG list IDs (1=pull, 2=collection, 3=wish, 5=read)
    that should be marked as active.
    """
    if active_lists is None:
        active_lists = []
    all_lists = [1, 2, 3, 5]
    controllers = ""
    for lid in all_lists:
        active = " active" if lid in active_lists else ""
        controllers += (
            f'<span class="comic-controller{active}" '
            f'data-comic="{comic_id}" data-list="{lid}"></span>'
        )
    return (
        f'<li class="issue" data-comic="{comic_id}" data-pulls="0" '
        f'data-potw="0" data-community="0">'
        f'{controllers}'
        f'<div class="title"><a href="/comic/{comic_id}/x">{name} #{comic_id}</a></div>'
        f'<div class="publisher">Test Pub</div>'
        f'</li>'
    )


def _make_list_response_with_lists(
    items: list[tuple[int, str, list[int]]],
    total_count: int,
) -> str:
    """Build a JSON response with list membership data.

    *items* is a list of (comic_id, name, active_list_ids) tuples.
    """
    html = "".join(
        _make_issue_html_with_lists(cid, name, active)
        for cid, name, active in items
    )
    return json.dumps({"count": total_count, "list": html})


def _make_list_response(comic_ids: list[int], total_count: int) -> str:
    """Build a JSON string mimicking the /comic/get_comics response."""
    html = "".join(_make_issue_html(cid) for cid in comic_ids)
    return json.dumps({"count": total_count, "list": html})


def test_cmd_search_returns_series(mock_client, search_series_json):
    resp = MagicMock()
    resp.text = json.dumps(search_series_json)
    mock_client.get.return_value = resp
    result = cmd_search(mock_client, "batman")
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0]["name"] == "100% DC"
    mock_client.get.assert_called_once()


def test_cmd_search_no_results(mock_client):
    resp = MagicMock()
    resp.text = json.dumps({"count": 0, "list": "<ul></ul>"})
    mock_client.get.return_value = resp
    result = cmd_search(mock_client, "zzzznonexistent")
    assert result == []


def test_cmd_releases_returns_issues(mock_client, releases_json):
    resp = MagicMock()
    resp.text = json.dumps(releases_json)
    mock_client.get.return_value = resp
    result = cmd_releases(mock_client)
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0]["id"] == 9559460


def test_cmd_releases_with_date(mock_client, releases_json):
    resp = MagicMock()
    resp.text = json.dumps(releases_json)
    mock_client.get.return_value = resp
    result = cmd_releases(mock_client, "2026-04-01")
    assert isinstance(result, list)
    # Verify the date was formatted correctly in the API call
    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"] if "params" in call_kwargs[1] else call_kwargs[0][1]
    assert params["date"] == "4/1/2026"


def test_cmd_collection_without_auth_raises(mock_client):
    mock_client.require_auth.side_effect = AuthRequired("Not logged in. Run: locg login")
    try:
        cmd_collection(mock_client)
        assert False, "Should have raised AuthRequired"
    except AuthRequired as e:
        assert "Not logged in" in str(e)


def test_cmd_collection_stale_session_raises(mock_client):
    """When the API returns data-user="0", detect expired session."""
    resp = MagicMock()
    resp.text = json.dumps({
        "count": 0,
        "list": '<ul data-user="0"></ul>',
    })
    mock_client.get.return_value = resp
    try:
        cmd_collection(mock_client)
        assert False, "Should have raised AuthRequired"
    except AuthRequired as e:
        assert "expired" in str(e).lower()


def test_cmd_add_posts_correct_data(mock_client):
    resp = MagicMock()
    resp.json.return_value = {"status": "ok"}
    mock_client.post.return_value = resp
    result = cmd_add(mock_client, "collection", 9559460)
    assert result == {"status": "ok"}
    mock_client.post.assert_called_once_with("/comic/my_list_move", data={
        "comic_id": 9559460,
        "list_id": 2,
        "action_id": 1,
    })


def test_cmd_add_invalid_list(mock_client):
    result = cmd_add(mock_client, "invalid", 123)
    assert "error" in result
    assert "Invalid list" in result["error"]


def test_cmd_remove_posts_correct_data(mock_client):
    resp = MagicMock()
    resp.json.return_value = {"status": "ok"}
    mock_client.post.return_value = resp
    result = cmd_remove(mock_client, "pull", 9559460)
    assert result == {"status": "ok"}
    mock_client.post.assert_called_once_with("/comic/my_list_move", data={
        "comic_id": 9559460,
        "list_id": 1,
        "action_id": 0,
    })


def test_get_week_date_formats_correctly():
    assert _get_week_date("2026-04-01") == "4/1/2026"
    assert _get_week_date("2026-12-25") == "12/25/2026"
    # Without target, returns some date in M/D/YYYY format
    result = _get_week_date()
    parts = result.split("/")
    assert len(parts) == 3


# --- Title filter tests (workaround for LOCG list+title API bug) ---

def test_filter_by_title_case_insensitive():
    issues = [
        {"id": 1, "name": "Batman #1"},
        {"id": 2, "name": "Superman #1"},
        {"id": 3, "name": "Batman/Superman #1"},
    ]
    result = _filter_by_title(issues, "batman")
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["id"] == 3


def test_filter_by_title_no_match():
    issues = [
        {"id": 1, "name": "Batman #1"},
        {"id": 2, "name": "Superman #1"},
    ]
    result = _filter_by_title(issues, "spider-man")
    assert result == []


def test_filter_by_title_empty_string_returns_all():
    """An empty title string should not filter anything (treated as falsy by caller)."""
    issues = [
        {"id": 1, "name": "Batman #1"},
        {"id": 2, "name": "Superman #1"},
    ]
    # _filter_by_title with empty string matches everything (empty needle)
    result = _filter_by_title(issues, "")
    assert len(result) == 2


def test_filter_by_title_substring_match():
    issues = [
        {"id": 1, "name": "The Amazing Spider-Man #100"},
        {"id": 2, "name": "Spider-Man 2099 #1"},
        {"id": 3, "name": "Batman #50"},
    ]
    result = _filter_by_title(issues, "spider-man")
    assert len(result) == 2
    assert all("Spider-Man" in i["name"] for i in result)


def test_cmd_collection_with_title_filter(mock_client, releases_json):
    """cmd_collection with title filters results client-side."""
    resp = MagicMock()
    resp.text = json.dumps(releases_json)
    mock_client.get.return_value = resp
    # The releases fixture has "Batman #8" as the first issue
    result = cmd_collection(mock_client, title="batman")
    assert isinstance(result, list)
    # All results should contain "batman" (case-insensitive) in the name
    for issue in result:
        assert "batman" in issue["name"].lower()


def test_cmd_collection_without_title_returns_all(mock_client, releases_json):
    """cmd_collection without title returns all issues unfiltered."""
    resp = MagicMock()
    resp.text = json.dumps(releases_json)
    mock_client.get.return_value = resp
    result_no_filter = cmd_collection(mock_client)
    assert isinstance(result_no_filter, list)
    assert len(result_no_filter) > 0


# --- Pagination tests ---

def test_get_user_list_single_page_no_pagination(mock_client):
    """When count <= items returned, no extra requests are made."""
    ids = list(range(1, 51))  # 50 items, well under 140
    resp = MagicMock()
    resp.text = _make_list_response(ids, total_count=50)
    mock_client.get.return_value = resp

    result = _get_user_list(mock_client, "collection")
    assert len(result) == 50
    # Only one GET call (no pagination needed)
    assert mock_client.get.call_count == 1


def test_get_user_list_paginates_two_pages(mock_client):
    """When count > items in first page, a second request is made."""
    page1_ids = list(range(1, 141))   # 140 items
    page2_ids = list(range(141, 201))  # 60 items
    total = 200

    resp1 = MagicMock()
    resp1.text = _make_list_response(page1_ids, total_count=total)
    resp2 = MagicMock()
    resp2.text = _make_list_response(page2_ids, total_count=total)
    mock_client.get.side_effect = [resp1, resp2]

    result = _get_user_list(mock_client, "collection")
    assert len(result) == 200
    assert mock_client.get.call_count == 2
    # Verify second call includes list_mode_offset
    second_call_params = mock_client.get.call_args_list[1][1]["params"]
    assert second_call_params["list_mode_offset"] == "140"


def test_get_user_list_paginates_three_pages(mock_client):
    """Three pages of results are fetched correctly."""
    page1_ids = list(range(1, 141))     # 140 items
    page2_ids = list(range(141, 281))   # 140 items
    page3_ids = list(range(281, 301))   # 20 items
    total = 300

    resp1 = MagicMock()
    resp1.text = _make_list_response(page1_ids, total_count=total)
    resp2 = MagicMock()
    resp2.text = _make_list_response(page2_ids, total_count=total)
    resp3 = MagicMock()
    resp3.text = _make_list_response(page3_ids, total_count=total)
    mock_client.get.side_effect = [resp1, resp2, resp3]

    result = _get_user_list(mock_client, "collection")
    assert len(result) == 300
    assert mock_client.get.call_count == 3
    # Check offsets
    assert "list_mode_offset" not in mock_client.get.call_args_list[0][1]["params"]
    assert mock_client.get.call_args_list[1][1]["params"]["list_mode_offset"] == "140"
    assert mock_client.get.call_args_list[2][1]["params"]["list_mode_offset"] == "280"


def test_get_user_list_stops_on_empty_page(mock_client):
    """If the server returns an empty page, pagination stops gracefully."""
    page1_ids = list(range(1, 141))  # 140 items
    total = 200  # Server claims 200 but second page is empty

    resp1 = MagicMock()
    resp1.text = _make_list_response(page1_ids, total_count=total)
    resp2 = MagicMock()
    resp2.text = _make_list_response([], total_count=total)
    mock_client.get.side_effect = [resp1, resp2]

    result = _get_user_list(mock_client, "collection")
    # Should return what we got (140), not loop forever
    assert len(result) == 140
    assert mock_client.get.call_count == 2


def test_get_user_list_deduplicates_overlapping_pages(mock_client):
    """If pages overlap (duplicate IDs), duplicates are removed."""
    page1_ids = list(range(1, 141))     # 140 items (1-140)
    page2_ids = list(range(131, 201))   # 70 items (131-200), 10 overlap
    total = 200

    resp1 = MagicMock()
    resp1.text = _make_list_response(page1_ids, total_count=total)
    resp2 = MagicMock()
    resp2.text = _make_list_response(page2_ids, total_count=total)
    mock_client.get.side_effect = [resp1, resp2]

    result = _get_user_list(mock_client, "collection")
    assert len(result) == 200  # 140 + 70 - 10 duplicates = 200
    # All IDs should be unique
    ids = [r["id"] for r in result]
    assert len(ids) == len(set(ids))


def test_get_user_list_exact_page_boundary(mock_client):
    """When count == _PAGE_SIZE exactly, a speculative fetch is needed.

    The LOCG API lies about total count (always reports 140), so when we
    get exactly 140 items we can't tell if there are more.  We must
    speculatively fetch page 2 to find out.  If it's empty, we stop.
    """
    ids = list(range(1, _PAGE_SIZE + 1))  # exactly 140
    resp1 = MagicMock()
    resp1.text = _make_list_response(ids, total_count=_PAGE_SIZE)
    resp2 = MagicMock()
    resp2.text = _make_list_response([], total_count=0)  # empty page 2
    mock_client.get.side_effect = [resp1, resp2]

    result = _get_user_list(mock_client, "collection")
    assert len(result) == _PAGE_SIZE
    assert mock_client.get.call_count == 2  # speculative fetch for page 2


def test_get_user_list_first_request_no_offset_param(mock_client):
    """The first request should NOT include list_mode_offset."""
    ids = list(range(1, 11))
    resp = MagicMock()
    resp.text = _make_list_response(ids, total_count=10)
    mock_client.get.return_value = resp

    _get_user_list(mock_client, "collection", order="alpha-asc")
    params = mock_client.get.call_args[1]["params"]
    assert "list_mode_offset" not in params
    assert params["list"] == "collection"
    assert params["order"] == "alpha-asc"


# --- Bug: LOCG API returns count == page size even when more items exist ---
#
# The real LOCG API returns count=140 and 140 items on every page, even when
# the user's collection has 500+ comics. The current pagination logic compares
# `offset < total_count` which is `140 < 140` → False, so it never fetches
# page 2.
#
# The fix should detect that count == _PAGE_SIZE (140) AND items == _PAGE_SIZE
# as a signal that there MAY be more pages, and speculatively fetch the next
# page. If the next page returns items, keep going. If empty, stop.
#
# This is the actual behavior observed against the live LOCG API on 2026-04-08.
# A collection with 500+ comics returns count=140 on every request. The
# list_mode_offset parameter DOES return different items per page — the server
# just reports count=140 regardless.

def test_get_user_list_paginates_when_count_equals_page_size(mock_client):
    """Bug: LOCG API reports count=140 even when more items exist.

    When the API returns count == _PAGE_SIZE (140) and exactly 140 items,
    the client should speculatively request the next page, because the
    server may have more data.  It should keep paginating until a page
    returns fewer than _PAGE_SIZE items.

    Real-world scenario: user has 350 comics. The API returns:
      Page 1: count=140, 140 items  (comics 1-140)
      Page 2: count=140, 140 items  (comics 141-280)
      Page 3: count=70,   70 items  (comics 281-350)
    Current code stops after page 1 because 140 < 140 is False.
    """
    page1_ids = list(range(1, 141))      # 140 items
    page2_ids = list(range(141, 281))    # 140 items
    page3_ids = list(range(281, 351))    # 70 items (final page)

    resp1 = MagicMock()
    resp1.text = _make_list_response(page1_ids, total_count=140)  # Bug: count=140
    resp2 = MagicMock()
    resp2.text = _make_list_response(page2_ids, total_count=140)  # Bug: count=140
    resp3 = MagicMock()
    resp3.text = _make_list_response(page3_ids, total_count=70)   # Final page
    mock_client.get.side_effect = [resp1, resp2, resp3]

    result = _get_user_list(mock_client, "collection")

    # Should have fetched ALL 350 items across 3 pages
    assert len(result) == 350, (
        f"Expected 350 items but got {len(result)}. "
        f"Pagination likely stopped after page 1 because count ({_PAGE_SIZE}) "
        f"== items returned ({_PAGE_SIZE}), but the server had more data. "
        f"Fix: when count == _PAGE_SIZE and items == _PAGE_SIZE, speculatively "
        f"fetch the next page."
    )
    assert mock_client.get.call_count == 3


def test_get_user_list_no_speculative_fetch_when_under_page_size(mock_client):
    """When count < _PAGE_SIZE, do NOT speculatively fetch another page.

    If a user has 50 comics, the API returns count=50, 50 items.
    No extra request should be made.
    """
    ids = list(range(1, 51))
    resp = MagicMock()
    resp.text = _make_list_response(ids, total_count=50)
    mock_client.get.return_value = resp

    result = _get_user_list(mock_client, "collection")
    assert len(result) == 50
    assert mock_client.get.call_count == 1


def test_get_user_list_speculative_fetch_stops_on_empty_page(mock_client):
    """If count == _PAGE_SIZE but the next page is empty, stop gracefully.

    Edge case: user has exactly 140 comics. API returns count=140, 140 items.
    We speculatively fetch page 2, get 0 items, and stop.
    """
    page1_ids = list(range(1, 141))

    resp1 = MagicMock()
    resp1.text = _make_list_response(page1_ids, total_count=140)
    resp2 = MagicMock()
    resp2.text = _make_list_response([], total_count=0)
    mock_client.get.side_effect = [resp1, resp2]

    result = _get_user_list(mock_client, "collection")
    assert len(result) == 140
    assert mock_client.get.call_count == 2  # One speculative fetch that returned empty


# --- List membership filtering tests (workaround for LOCG list param bug) ---


def test_filter_by_list_membership_keeps_matching_items():
    """Items with lists[list_name]=True are kept."""
    issues = [
        {"id": 1, "name": "A", "lists": {"pull": False, "collection": True, "wish": False, "read": False}},
        {"id": 2, "name": "B", "lists": {"pull": False, "collection": False, "wish": True, "read": False}},
        {"id": 3, "name": "C", "lists": {"pull": False, "collection": True, "wish": False, "read": True}},
    ]
    result = _filter_by_list_membership(issues, "collection")
    assert len(result) == 2
    assert [r["id"] for r in result] == [1, 3]


def test_filter_by_list_membership_filters_wish_list():
    """Filtering for wish list keeps only wish=True items."""
    issues = [
        {"id": 1, "name": "A", "lists": {"pull": False, "collection": True, "wish": False, "read": False}},
        {"id": 2, "name": "B", "lists": {"pull": False, "collection": False, "wish": True, "read": False}},
        {"id": 3, "name": "C", "lists": {"pull": True, "collection": False, "wish": True, "read": False}},
    ]
    result = _filter_by_list_membership(issues, "wish")
    assert len(result) == 2
    assert [r["id"] for r in result] == [2, 3]


def test_filter_by_list_membership_keeps_items_with_none_lists():
    """Items with lists=None (unauthenticated) are kept, not dropped."""
    issues = [
        {"id": 1, "name": "A", "lists": None},
        {"id": 2, "name": "B", "lists": {"pull": False, "collection": True, "wish": False, "read": False}},
        {"id": 3, "name": "C", "lists": None},
    ]
    result = _filter_by_list_membership(issues, "collection")
    assert len(result) == 3  # All kept: 2 with None + 1 matching


def test_filter_by_list_membership_removes_all_non_matching():
    """When no items match the list, result is empty."""
    issues = [
        {"id": 1, "name": "A", "lists": {"pull": False, "collection": True, "wish": False, "read": False}},
        {"id": 2, "name": "B", "lists": {"pull": False, "collection": True, "wish": False, "read": False}},
    ]
    result = _filter_by_list_membership(issues, "wish")
    assert result == []


def test_filter_by_list_membership_noop_when_all_match():
    """When all items are on the requested list, nothing is removed (no-op)."""
    issues = [
        {"id": 1, "name": "A", "lists": {"pull": False, "collection": True, "wish": False, "read": False}},
        {"id": 2, "name": "B", "lists": {"pull": False, "collection": True, "wish": False, "read": False}},
    ]
    result = _filter_by_list_membership(issues, "collection")
    assert len(result) == 2


def test_filter_by_list_membership_empty_input():
    """Empty input list returns empty output."""
    result = _filter_by_list_membership([], "collection")
    assert result == []


def test_get_user_list_filters_by_list_membership(mock_client):
    """_get_user_list should filter results to only include items on the requested list.

    This is the core fix for the LOCG API bug where the list parameter is ignored.
    """
    # Simulate API returning comics from ALL lists (the bug)
    items = [
        (1, "Batman", [2]),        # collection only
        (2, "Superman", [3]),      # wish only
        (3, "Flash", [2, 5]),      # collection + read
        (4, "Aquaman", [1]),       # pull only
        (5, "Wonder Woman", [2]),  # collection only
    ]
    resp = MagicMock()
    resp.text = _make_list_response_with_lists(items, total_count=5)
    mock_client.get.return_value = resp

    result = _get_user_list(mock_client, "collection")
    assert len(result) == 3
    result_ids = [r["id"] for r in result]
    assert 1 in result_ids   # Batman - in collection
    assert 3 in result_ids   # Flash - in collection
    assert 5 in result_ids   # Wonder Woman - in collection
    assert 2 not in result_ids  # Superman - wish only
    assert 4 not in result_ids  # Aquaman - pull only


def test_get_user_list_filters_wish_list(mock_client):
    """cmd_wish_list should only return items on the wish list."""
    items = [
        (1, "Batman", [2]),        # collection only
        (2, "Superman", [3]),      # wish only
        (3, "Flash", [3, 2]),      # wish + collection
    ]
    resp = MagicMock()
    resp.text = _make_list_response_with_lists(items, total_count=3)
    mock_client.get.return_value = resp

    result = cmd_wish_list(mock_client)
    assert len(result) == 2
    result_ids = [r["id"] for r in result]
    assert 2 in result_ids   # Superman - on wish
    assert 3 in result_ids   # Flash - on wish
    assert 1 not in result_ids  # Batman - collection only


def test_get_user_list_filters_pull_list(mock_client):
    """cmd_pull_list should only return items on the pull list."""
    items = [
        (1, "Batman", [1, 2]),     # pull + collection
        (2, "Superman", [2]),      # collection only
        (3, "Flash", [1]),         # pull only
    ]
    resp = MagicMock()
    resp.text = _make_list_response_with_lists(items, total_count=3)
    mock_client.get.return_value = resp

    result = cmd_pull_list(mock_client)
    assert len(result) == 2
    result_ids = [r["id"] for r in result]
    assert 1 in result_ids
    assert 3 in result_ids


def test_get_user_list_filters_read_list(mock_client):
    """cmd_read_list should only return items on the read list."""
    items = [
        (1, "Batman", [5]),        # read only
        (2, "Superman", [2]),      # collection only
        (3, "Flash", [5, 2]),      # read + collection
    ]
    resp = MagicMock()
    resp.text = _make_list_response_with_lists(items, total_count=3)
    mock_client.get.return_value = resp

    result = cmd_read_list(mock_client)
    assert len(result) == 2
    result_ids = [r["id"] for r in result]
    assert 1 in result_ids
    assert 3 in result_ids


def test_get_user_list_title_filter_applies_after_list_filter(mock_client):
    """Title filter should apply AFTER list membership filter.

    If we have Batman in collection and Batman on wish list,
    filtering collection + title=batman should only return the collection one.
    """
    items = [
        (1, "Batman", [2]),        # collection only
        (2, "Batman Wish", [3]),   # wish only (has "batman" in name)
        (3, "Superman", [2]),      # collection only
    ]
    resp = MagicMock()
    resp.text = _make_list_response_with_lists(items, total_count=3)
    mock_client.get.return_value = resp

    result = cmd_collection(mock_client, title="batman")
    # Should get only Batman #1 (in collection AND matches title)
    # NOT Batman Wish #2 (matches title but NOT in collection)
    assert len(result) == 1
    assert result[0]["id"] == 1


# --- cmd_check_lists tests ---


def _make_comic_detail_html(comic_id: int, name: str, list_states: dict[int, bool] | None = None) -> str:
    """Build minimal comic detail HTML for testing cmd_check_lists.

    list_states maps list_id (1=pull, 2=collection, 3=wish, 5=read) to active bool.
    If None, simulates unauthenticated (no data-list attributes).
    """
    controllers = ""
    if list_states is not None:
        for list_id, active in list_states.items():
            cls = "comic-controller active" if active else "comic-controller"
            controllers += f'<div class="{cls}" data-list="{list_id}"></div>\n'
    else:
        controllers = '<div class="comic-controller" data-toggle="modal" data-target="#modal-login"></div>'

    return f"""
    <html><head>
    <link rel="canonical" href="https://leagueofcomicgeeks.com/comic/{comic_id}/{name.lower().replace(' ', '-')}"/>
    <meta property="og:description" content="Test"/>
    <meta property="og:image" content="https://example.com/cover.jpg"/>
    </head><body>
    <h1>{name}</h1>
    {controllers}
    </body></html>
    """


def test_cmd_check_lists_single_comic(mock_client):
    """Check list membership for a single comic."""
    html = _make_comic_detail_html(9559460, "Batman #8", {1: False, 2: True, 3: False, 5: False})
    resp = MagicMock()
    resp.status_code = 200
    resp.text = html
    mock_client.get.return_value = resp

    result = cmd_check_lists(mock_client, [9559460])
    assert len(result) == 1
    assert result[0]["id"] == 9559460
    assert result[0]["name"] == "Batman #8"
    assert result[0]["lists"]["collection"] is True
    assert result[0]["lists"]["pull"] is False
    mock_client.require_auth.assert_called_once()


def test_cmd_check_lists_multiple_comics(mock_client):
    """Check list membership for multiple comics."""
    html1 = _make_comic_detail_html(100, "Batman #1", {1: False, 2: True, 3: False, 5: False})
    html2 = _make_comic_detail_html(200, "Superman #1", {1: False, 2: False, 3: True, 5: False})
    html3 = _make_comic_detail_html(300, "Flash #1", {1: True, 2: True, 3: False, 5: True})

    resp1 = MagicMock(status_code=200, text=html1)
    resp2 = MagicMock(status_code=200, text=html2)
    resp3 = MagicMock(status_code=200, text=html3)
    mock_client.get.side_effect = [resp1, resp2, resp3]

    result = cmd_check_lists(mock_client, [100, 200, 300])
    assert len(result) == 3

    assert result[0]["id"] == 100
    assert result[0]["lists"]["collection"] is True

    assert result[1]["id"] == 200
    assert result[1]["lists"]["wish"] is True
    assert result[1]["lists"]["collection"] is False

    assert result[2]["id"] == 300
    assert result[2]["lists"]["pull"] is True
    assert result[2]["lists"]["collection"] is True
    assert result[2]["lists"]["read"] is True

    assert mock_client.get.call_count == 3


def test_cmd_check_lists_handles_404(mock_client):
    """Invalid comic IDs should return error entries, not crash."""
    html = _make_comic_detail_html(100, "Batman #1", {1: False, 2: True, 3: False, 5: False})
    resp_ok = MagicMock(status_code=200, text=html)
    resp_404 = MagicMock(status_code=404)
    mock_client.get.side_effect = [resp_ok, resp_404]

    result = cmd_check_lists(mock_client, [100, 999999])
    assert len(result) == 2

    assert result[0]["id"] == 100
    assert result[0]["lists"]["collection"] is True

    assert result[1]["id"] == 999999
    assert result[1]["name"] is None
    assert result[1]["lists"] is None
    assert result[1]["error"] == "not found"


def test_cmd_check_lists_requires_auth(mock_client):
    """cmd_check_lists should require authentication."""
    mock_client.require_auth.side_effect = AuthRequired("Not logged in. Run: locg login")
    try:
        cmd_check_lists(mock_client, [100])
        assert False, "Should have raised AuthRequired"
    except AuthRequired as e:
        assert "Not logged in" in str(e)
    # Should not have made any HTTP requests
    mock_client.get.assert_not_called()


def test_cmd_check_lists_empty_ids(mock_client):
    """Empty list of IDs should return empty results."""
    result = cmd_check_lists(mock_client, [])
    assert result == []
    mock_client.get.assert_not_called()
