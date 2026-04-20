"""Tests for locg.client module."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from locg.client import AuthRequired, LOCGClient


def _make_client_with_session(ci_session: str | None = "abc123") -> LOCGClient:
    """Build an LOCGClient without touching the filesystem."""
    with patch.object(LOCGClient, "_load_cookies"):
        client = LOCGClient()
    # Install a fake cookie jar
    jar = []
    if ci_session:
        cookie = MagicMock()
        cookie.name = "ci_session"
        cookie.value = ci_session
        jar.append(cookie)
    client._session = MagicMock()
    client._session.cookies.jar = jar
    return client


def test_require_auth_verifies_once():
    """require_auth should call verify_session at most once per LOCGClient instance."""
    client = _make_client_with_session()
    client.verify_session = MagicMock(return_value=True)

    client.require_auth()
    client.require_auth()
    client.require_auth()

    assert client.verify_session.call_count == 1


def test_require_auth_expired_session_raises():
    """If verify_session returns False, require_auth should raise AuthRequired."""
    client = _make_client_with_session()
    client.verify_session = MagicMock(return_value=False)

    with pytest.raises(AuthRequired, match="Session expired"):
        client.require_auth()


def test_require_auth_no_cookie_raises():
    """Without a ci_session cookie, require_auth raises before verify_session."""
    client = _make_client_with_session(ci_session=None)
    client.verify_session = MagicMock(return_value=True)

    with pytest.raises(AuthRequired, match="Not logged in"):
        client.require_auth()

    client.verify_session.assert_not_called()


def test_require_auth_does_not_cache_on_transient_error():
    """If verify_session raises, the next require_auth should retry (not cache the failure)."""
    client = _make_client_with_session()
    call_count = {"n": 0}

    def side_effect():
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated 429")
        return True

    client.verify_session = MagicMock(side_effect=side_effect)

    # First call — the exception propagates; we should NOT catch AuthRequired,
    # we should catch RuntimeError specifically.
    with pytest.raises(RuntimeError, match="simulated 429"):
        client.require_auth()

    # _server_auth_verified should still be None (not cached)
    assert client._server_auth_verified is None

    # Second call — verify_session is called again, returns True, no raise
    client.require_auth()
    assert call_count["n"] == 2
    assert client._server_auth_verified is True


def test_login_success_primes_verified_cache():
    """On successful login, _server_auth_verified should be True so
    the next require_auth call doesn't re-verify."""
    client = _make_client_with_session(ci_session=None)  # start empty

    # Fake login that sets the cookie then returns success
    def fake_post(path, data=None):
        cookie = MagicMock()
        cookie.name = "ci_session"
        cookie.value = "xyz"
        client._session.cookies.jar.append(cookie)
        resp = MagicMock()
        resp.status_code = 200
        return resp

    client.post = MagicMock(side_effect=fake_post)
    client._save_cookies = MagicMock()
    client.verify_session = MagicMock(return_value=True)

    assert client.login("user", "pass") is True
    assert client._server_auth_verified is True

    # Now require_auth should NOT call verify_session again
    client.require_auth()
    assert client.verify_session.call_count == 1  # only the one from login()
