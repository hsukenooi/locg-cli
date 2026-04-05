"""Tests for locg.models module."""
from __future__ import annotations

import json

from bs4 import BeautifulSoup

from locg.models import _safe_int, extract_comic_detail, extract_issue, extract_series


def test_extract_issue_from_fixture(releases_json):
    html = releases_json["list"]
    soup = BeautifulSoup(html, "html.parser")
    li = soup.find("li", class_="issue")
    issue = extract_issue(li)
    assert issue["id"] == 9559460
    assert issue["name"] == "Batman #8"
    assert issue["publisher"] == "DC Comics"
    assert issue["price"] == 4.99
    assert issue["pulls"] == 32597
    assert issue["potw"] == 11
    assert issue["community_rating"] == 95
    assert "leagueofcomicgeeks.com" in issue["url"]


def test_extract_series_from_fixture(search_series_json):
    html = search_series_json["list"]
    soup = BeautifulSoup(html, "html.parser")
    li = soup.find("li")
    series = extract_series(li)
    assert series["id"] == 188765
    assert series["name"] == "100% DC"
    assert series["publisher"] == "Panini Comics"
    assert series["start_year"] == 2005
    assert series["end_year"] == 2011
    assert series["issue_count"] == 4
    assert "leagueofcomicgeeks.com" in series["url"]


def test_extract_issue_handles_empty_community(releases_json):
    html = releases_json["list"]
    soup = BeautifulSoup(html, "html.parser")
    # Find a variant with data-community=""
    items = soup.find_all("li", class_="issue")
    empty_found = False
    for li in items:
        if li.get("data-community") == "":
            issue = extract_issue(li)
            assert issue["community_rating"] == 0
            empty_found = True
            break
    if not empty_found:
        # Test with synthetic HTML
        synthetic = '<li class="issue" data-comic="123" data-pulls="0" data-potw="0" data-community="" data-parent="0"><div class="title"><a href="/comic/123/test">Test</a></div><div class="publisher">Test Pub</div></li>'
        li = BeautifulSoup(synthetic, "html.parser").find("li")
        issue = extract_issue(li)
        assert issue["community_rating"] == 0


def test_extract_comic_detail_from_fixture(comic_detail_html):
    soup = BeautifulSoup(comic_detail_html, "html.parser")
    detail = extract_comic_detail(soup)
    assert detail["name"] == "Batman #8"
    assert detail["id"] == 9559460
    assert detail["publisher"] == "DC Comics"
    assert detail["store_date"] == "Apr 1, 2026"
    assert detail["price"] == 4.99
    assert detail["pages"] == 36
    assert detail["cover_date"] == "Jun 2026"
    assert detail["upc"] == "76194139163200811"
    assert detail["sku"] == "0226DC0057"
    assert detail["community_rating"] == 3.8
    assert detail["rating_count"] == 2493
    assert detail["series_id"] == 186408


def test_safe_int_handles_empty_and_none():
    assert _safe_int("") == 0
    assert _safe_int(None) == 0
    assert _safe_int("42") == 42
    assert _safe_int("abc") == 0
    assert _safe_int(None, default=5) == 5
