"""Bearer-key auth dependency.

The API accepts a key via `X-API-Key: <key>` or `Authorization: Bearer <key>`.
Keys are configured with OPENMONTAGE_API_KEYS (comma-separated). When none are
set, auth is disabled — convenient for local dev, but the service should never
be exposed publicly without keys. In the Coolify/MCP-gateway topology the
gateway holds the key and injects it on each call.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from .config import get_settings


def require_api_key(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    if not settings.auth_enabled:
        return
    presented = x_api_key
    if not presented and authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:].strip()
    if not presented or presented not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid API key",
        )
