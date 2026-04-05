"""Tests for locg.commands module."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from locg.client import AuthRequired
from locg.commands import (
    _get_week_date,
    cmd_add,
    cmd_collection,
    cmd_releases,
    cmd_remove,
    cmd_search,
)


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
