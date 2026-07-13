"""Human operator authentication: Titanium magic-link -> signed session cookie.

Two audiences reach this API. Machines (MCP servers, Edge AIOS) authenticate
with an API key (see api/auth.py). Humans — the operator who authorises the
agent at /setup — log in with their real identity through Titanium Licensing's
hosted magic-link flow, and carry a signed session cookie afterwards.

The flow (AUTH_ONLY_MODE — identity only, no license key in v1):

    POST /auth/login {email}
        -> portal /api/auth/send-magic-link  (email lands in the operator's inbox)
    operator clicks the link
        -> portal redirects to  <returnUrl>?act=<activation-token>
    GET /auth/callback?act=...
        -> portal /api/exchange {act}  -> {email, licenseKey}
        -> we mint a signed session cookie and redirect to /setup

The session cookie is a stdlib-signed `<payload>.<hmac>` — no new dependency,
no server-side session store. The signing secret is persisted on the jobs
volume so sessions survive redeploys; it is generated once if absent.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from .config import Settings

COOKIE_NAME = "om_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600  # a week; re-login via magic link after


@dataclass(frozen=True)
class Session:
    email: str
    issued_at: int
    expires_at: int


class SessionManager:
    """Signs and verifies operator session cookies."""

    def __init__(self, settings: Settings):
        self._s = settings
        self._secret = _load_or_create_secret(settings.jobs_dir / "session_secret")

    # ---- cookie sign / verify ---------------------------------------------

    def issue(self, email: str) -> str:
        now = int(time.time())
        payload = {"email": email, "iat": now, "exp": now + SESSION_TTL_SECONDS}
        raw = _b64e(json.dumps(payload, separators=(",", ":")).encode())
        sig = self._sign(raw)
        return f"{raw}.{sig}"

    def verify(self, cookie: str | None) -> Session | None:
        if not cookie or "." not in cookie:
            return None
        raw, _, sig = cookie.partition(".")
        expected = self._sign(raw)
        if not hmac.compare_digest(sig, expected):
            return None
        try:
            data = json.loads(_b64d(raw))
        except (ValueError, json.JSONDecodeError):
            return None
        email = data.get("email")
        exp = int(data.get("exp", 0))
        if not email or exp < int(time.time()):
            return None
        return Session(email=email, issued_at=int(data.get("iat", 0)), expires_at=exp)

    def _sign(self, raw: str) -> str:
        return _b64e(hmac.new(self._secret, raw.encode(), hashlib.sha256).digest())


class PortalClient:
    """Thin client for the Titanium License Portal's stack-agnostic HTTP API."""

    def __init__(self, settings: Settings):
        self._base = settings.titanium_portal_url.rstrip("/")
        self._app_id = settings.titanium_app_id
        self._return_url = settings.titanium_return_url

    @property
    def configured(self) -> bool:
        return bool(self._base and self._app_id and self._return_url)

    async def send_magic_link(self, email: str) -> None:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.post(
                f"{self._base}/api/auth/send-magic-link",
                json={"email": email, "appId": self._app_id, "returnUrl": self._return_url},
            )
        if r.status_code != 200:
            raise PortalError(_error_detail(r), r.status_code)

    async def exchange(self, act: str) -> str:
        """Exchange an activation token for the authenticated email."""
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.post(f"{self._base}/api/exchange", json={"act": act})
        if r.status_code != 200:
            raise PortalError(_error_detail(r), r.status_code)
        email = (r.json() or {}).get("email")
        if not email:
            raise PortalError("exchange returned no email", 502)
        return email


class PortalError(Exception):
    def __init__(self, detail: str, status: int):
        super().__init__(detail)
        self.detail = detail
        self.status = status


# ---- helpers ---------------------------------------------------------------


def _load_or_create_secret(path: Path) -> bytes:
    if path.exists():
        data = path.read_bytes().strip()
        if len(data) >= 32:
            return data
    secret = secrets.token_bytes(32)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(secret)
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return secret


def _error_detail(r: httpx.Response) -> str:
    try:
        return (r.json() or {}).get("error", f"portal returned {r.status_code}")
    except ValueError:
        return f"portal returned {r.status_code}"


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)
