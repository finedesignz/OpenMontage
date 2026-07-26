"""Bearer-key auth dependency (machine callers).

The API accepts a key via `X-API-Key: <key>` or `Authorization: Bearer <key>`.
Keys are configured with OPENMONTAGE_API_KEYS (comma-separated). This is the
credential MCP servers and the gateway use; human operators use the Titanium
session instead (see api/session.py).

Auth may only be disabled by explicit opt-in (OPENMONTAGE_ALLOW_NO_AUTH=1) for
local dev. A public bind with no keys and no opt-in refuses to boot — see
config.validate_boot(). We never silently fail open on a misconfigured deploy.
"""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from .config import get_settings


def _key_accepted(presented: str, configured: list[str]) -> bool:
    # Constant-time compare so a network attacker cannot recover a key byte by
    # byte from response timing. Compare against every configured key (not a
    # membership test, which short-circuits on the first differing byte).
    accepted = False
    for key in configured:
        # A non-ASCII presented key (Starlette decodes headers as latin-1, so a
        # hostile `X-API-Key: \xff` yields a non-ASCII str) makes compare_digest
        # raise TypeError. Such a key can never equal a configured key, so treat
        # the TypeError as a non-match — this keeps the 401 contract (not 500)
        # while preserving the loop-over-all-keys constant-time property.
        try:
            if hmac.compare_digest(presented, key):
                accepted = True
        except TypeError:
            pass
    return accepted


def require_api_key(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    if not settings.auth_enabled:
        # Only reachable when OPENMONTAGE_ALLOW_NO_AUTH=1; validate_boot() has
        # already refused a public bind without keys.
        return
    presented = x_api_key
    if not presented and authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:].strip()
    if not presented or not _key_accepted(presented, settings.api_keys):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid API key",
        )
