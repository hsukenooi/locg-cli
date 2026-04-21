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


def test_require_auth_expired_session_raises(monkeypatch):
    """If verify_session returns False, require_auth should raise AuthRequired."""
    monkeypatch.delenv("LOCG_USERNAME", raising=False)
    monkeypatch.delenv("LOCG_PASSWORD", raising=False)
    client = _make_client_with_session()
    client.verify_session = MagicMock(return_value=False)

    with pytest.raises(AuthRequired, match="Session expired"):
        client.require_auth()


def test_require_auth_no_cookie_raises(monkeypatch):
    """Without a ci_session cookie, require_auth raises before verify_session."""
    monkeypatch.delenv("LOCG_USERNAME", raising=False)
    monkeypatch.delenv("LOCG_PASSWORD", raising=False)
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


def test_require_auth_expired_triggers_env_auto_login(monkeypatch):
    """Expired session with LOCG_USERNAME/LOCG_PASSWORD in env should auto-login."""
    client = _make_client_with_session()
    client.verify_session = MagicMock(return_value=False)
    client.login = MagicMock(return_value=True)

    monkeypatch.setenv("LOCG_USERNAME", "user")
    monkeypatch.setenv("LOCG_PASSWORD", "pass")

    client.require_auth()  # should NOT raise
    client.login.assert_called_once_with("user", "pass")


def test_require_auth_expired_no_env_still_raises(monkeypatch):
    """Without env creds, expired session still raises AuthRequired."""
    client = _make_client_with_session()
    client.verify_session = MagicMock(return_value=False)
    client.login = MagicMock(return_value=True)

    monkeypatch.delenv("LOCG_USERNAME", raising=False)
    monkeypatch.delenv("LOCG_PASSWORD", raising=False)

    with pytest.raises(AuthRequired, match="Session expired"):
        client.require_auth()
    client.login.assert_not_called()


def test_require_auth_auto_login_failure_raises(monkeypatch):
    """If env creds are set but login fails, still raise AuthRequired."""
    client = _make_client_with_session()
    client.verify_session = MagicMock(return_value=False)
    client.login = MagicMock(return_value=False)  # login fails

    monkeypatch.setenv("LOCG_USERNAME", "user")
    monkeypatch.setenv("LOCG_PASSWORD", "wrong")

    with pytest.raises(AuthRequired, match="Session expired"):
        client.require_auth()
    client.login.assert_called_once_with("user", "wrong")


def test_require_auth_no_cookie_triggers_env_auto_login(monkeypatch):
    """Missing ci_session cookie should also attempt auto-login when env creds set."""
    client = _make_client_with_session(ci_session=None)
    client.login = MagicMock(return_value=True)

    monkeypatch.setenv("LOCG_USERNAME", "user")
    monkeypatch.setenv("LOCG_PASSWORD", "pass")

    client.require_auth()
    client.login.assert_called_once_with("user", "pass")


def test_require_auth_env_login_swallows_exception(monkeypatch):
    """A rate-limit or network error during auto-login must surface as
    AuthRequired — never as a raw exception — so the CLI produces a clean
    exit-1 auth error instead of an exit-4 unexpected error."""
    client = _make_client_with_session()
    client.verify_session = MagicMock(return_value=False)
    client.login = MagicMock(side_effect=Exception("Rate limited. Retry after 60s"))

    monkeypatch.setenv("LOCG_USERNAME", "user")
    monkeypatch.setenv("LOCG_PASSWORD", "pass")

    with pytest.raises(AuthRequired, match="Session expired"):
        client.require_auth()


def test_require_auth_env_login_sets_verified_flag(monkeypatch):
    """After a successful env auto-login, _server_auth_verified must be True
    so the next require_auth() skips verify_session. The invariant cannot
    rely on login()'s internal side effects because tests (and future
    refactors) may bypass them."""
    client = _make_client_with_session(ci_session=None)
    client.login = MagicMock(return_value=True)

    monkeypatch.setenv("LOCG_USERNAME", "user")
    monkeypatch.setenv("LOCG_PASSWORD", "pass")

    client.require_auth()
    assert client._server_auth_verified is True


def test_require_auth_partial_env_does_not_login(monkeypatch):
    """Only one of LOCG_USERNAME/LOCG_PASSWORD set — no auto-login attempt."""
    client = _make_client_with_session()
    client.verify_session = MagicMock(return_value=False)
    client.login = MagicMock(return_value=True)

    monkeypatch.setenv("LOCG_USERNAME", "user")
    monkeypatch.delenv("LOCG_PASSWORD", raising=False)

    with pytest.raises(AuthRequired, match="Session expired"):
        client.require_auth()
    client.login.assert_not_called()


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
