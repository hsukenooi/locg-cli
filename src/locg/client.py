"""HTTP client for League of Comic Geeks with Cloudflare bypass."""
from __future__ import annotations

import json
import sys
import time
from typing import Any, Optional
from urllib.parse import urlencode

from curl_cffi import requests as cffi_requests

from locg.config import cookie_path, ensure_config_dir

BASE_URL = "https://leagueofcomicgeeks.com"
_DEBUG = False


def set_debug(enabled: bool) -> None:
    global _DEBUG
    _DEBUG = enabled


def _debug(msg: str) -> None:
    if _DEBUG:
        print(f"[debug] {msg}", file=sys.stderr)


class AuthRequired(Exception):
    """Raised when a command requires authentication."""
    pass


class LOCGClient:
    """HTTP client that impersonates Chrome to bypass Cloudflare."""

    def __init__(self) -> None:
        self._session = cffi_requests.Session(impersonate="chrome")
        self._cookies_loaded = False
        self._load_cookies()

    def _load_cookies(self) -> None:
        p = cookie_path()
        if p.exists():
            with open(p) as f:
                cookies = json.load(f)
            for name, value in cookies.items():
                self._session.cookies.set(name, value, domain="leagueofcomicgeeks.com")
            self._cookies_loaded = True
            _debug(f"Loaded {len(cookies)} cookies from {p}")

    def _save_cookies(self) -> None:
        ensure_config_dir()
        p = cookie_path()
        cookies = {}
        for cookie in self._session.cookies.jar:
            cookies[cookie.name] = cookie.value
        with open(p, "w") as f:
            json.dump(cookies, f, indent=2)
        _debug(f"Saved {len(cookies)} cookies to {p}")

    @property
    def is_authenticated(self) -> bool:
        for cookie in self._session.cookies.jar:
            if cookie.name == "ci_session":
                return True
        return False

    def require_auth(self) -> None:
        if not self.is_authenticated:
            raise AuthRequired("Not logged in. Run: locg login")

    def get(self, path: str, params: Optional[dict[str, Any]] = None) -> cffi_requests.Response:
        url = f"{BASE_URL}{path}"
        if params:
            url = f"{url}?{urlencode(params, doseq=True)}"
        _debug(f"GET {url}")
        start = time.monotonic()
        resp = self._session.get(url, timeout=30)
        elapsed = time.monotonic() - start
        _debug(f"  -> {resp.status_code} ({elapsed:.2f}s, {len(resp.content)} bytes)")
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "60")
            raise Exception(f"Rate limited. Retry after {retry_after}s")
        return resp

    def post(self, path: str, data: Optional[dict[str, Any]] = None) -> cffi_requests.Response:
        url = f"{BASE_URL}{path}"
        _debug(f"POST {url}")
        start = time.monotonic()
        resp = self._session.post(url, data=data, timeout=30)
        elapsed = time.monotonic() - start
        _debug(f"  -> {resp.status_code} ({elapsed:.2f}s)")
        self._save_cookies()
        return resp

    def verify_session(self) -> bool:
        """Check if the current session is valid by making a lightweight request.

        Returns True if the server recognizes us as a logged-in user.
        """
        from locg.parser import parse_list_response
        resp = self.get("/comic/get_comics", params={
            "list": "collection",
            "view": "thumbs",
        })
        _count, soup = parse_list_response(resp.text)
        tag = soup.find(attrs={"data-user": "0"})
        is_valid = tag is None
        _debug(f"Session verification: {'valid' if is_valid else 'invalid (data-user=0)'}")
        return is_valid

    def login(self, username: str, password: str) -> bool:
        """Log in and persist the session cookie. Returns True on success."""
        resp = self.post("/login", data={
            "username": username,
            "password": password,
        })
        if not self.is_authenticated:
            _debug(f"Login failed: no ci_session cookie (status {resp.status_code})")
            return False

        self._save_cookies()

        # Verify the session is actually valid server-side
        if not self.verify_session():
            _debug("Login appeared to succeed but session is not valid server-side")
            return False

        _debug("Login successful (verified)")
        return True

    def close(self) -> None:
        self._session.close()
