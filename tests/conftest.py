"""Shared fixtures for locg tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES


@pytest.fixture
def releases_json():
    with open(FIXTURES / "releases.json") as f:
        return json.load(f)


@pytest.fixture
def search_series_json():
    with open(FIXTURES / "search_series.json") as f:
        return json.load(f)


@pytest.fixture
def series_issues_json():
    with open(FIXTURES / "series_issues.json") as f:
        return json.load(f)


@pytest.fixture
def comic_detail_html():
    with open(FIXTURES / "comic_detail.html") as f:
        return f.read()


@pytest.fixture
def mock_client():
    """A mock LOCGClient with get/post as MagicMocks."""
    client = MagicMock()
    client.is_authenticated = True
    client.require_auth = MagicMock()
    client.close = MagicMock()
    return client
