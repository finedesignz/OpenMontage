"""API configuration, read from environment at startup.

Everything is env-driven so Coolify is the single source of truth. No secrets
live in the repo. The only values the API itself needs are the auth key and a
few runtime knobs; all *provider* keys (FAL_KEY, OPENAI_API_KEY, ...) are read
by the OpenMontage tools themselves, exactly as in CLI mode.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _keys(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    return [k.strip() for k in raw.split(",") if k.strip()]


@dataclass(frozen=True)
class Settings:
    # --- Auth ---------------------------------------------------------------
    # Comma-separated bearer keys accepted on the X-API-Key header (or
    # `Authorization: Bearer <key>`). Empty list => auth DISABLED (dev only).
    api_keys: list[str] = field(default_factory=lambda: _keys("OPENMONTAGE_API_KEYS"))

    # --- Runtime ------------------------------------------------------------
    host: str = os.environ.get("HOST", "0.0.0.0")
    port: int = _int("PORT", 8080)
    # Max concurrent production jobs (each spawns a headless agent — heavy).
    max_concurrency: int = _int("OPENMONTAGE_MAX_CONCURRENCY", 2)
    # Hard wall-clock ceiling for a single job before it is killed.
    job_timeout_seconds: int = _int("OPENMONTAGE_JOB_TIMEOUT", 3600)

    # --- Agent runtime ------------------------------------------------------
    # Path to the Claude Code CLI binary used to drive a job headlessly.
    claude_bin: str = os.environ.get("OPENMONTAGE_CLAUDE_BIN", "claude")
    agent_model: str = os.environ.get("OPENMONTAGE_AGENT_MODEL", "")  # "" => CLI default
    # A full production (research -> proposal -> script -> scene plan -> assets ->
    # edit -> compose) burned through 120 turns before reaching compose. The cap
    # is a runaway guard, not a budget — spend is capped separately by budget_usd.
    agent_max_turns: int = _int("OPENMONTAGE_AGENT_MAX_TURNS", 400)
    # Per-job budget cap (USD) handed to the agent. Mirrors the app's own
    # budget governance default ($10).
    budget_usd: float = float(os.environ.get("OPENMONTAGE_BUDGET_USD", "10") or "10")

    # --- Human operator auth (Titanium magic-link) --------------------------
    # AUTH_ONLY_MODE: identity only, no license key needed. When the portal URL
    # + app id + return URL are all set, /setup requires an operator login.
    titanium_portal_url: str = field(
        default_factory=lambda: os.environ.get("TITANIUM_PORTAL_URL", "https://license.titaniumlabs.us")
    )
    titanium_app_id: str = field(default_factory=lambda: os.environ.get("TITANIUM_APP_ID", ""))
    titanium_return_url: str = field(default_factory=lambda: os.environ.get("TITANIUM_RETURN_URL", ""))
    # Optional allowlist of emails permitted to log in (comma-separated). Empty
    # => any address the portal will send a link to may authenticate.
    operator_emails: list[str] = field(default_factory=lambda: _keys("OPENMONTAGE_OPERATOR_EMAILS"))

    # --- Storage ------------------------------------------------------------
    repo_root: Path = REPO_ROOT
    jobs_dir: Path = field(default_factory=lambda: REPO_ROOT / "jobs")
    projects_dir: Path = field(default_factory=lambda: REPO_ROOT / "projects")

    # Explicit dev opt-out. Without keys AND without this flag, a non-loopback
    # bind refuses to boot rather than serving every route unauthenticated.
    allow_no_auth: bool = field(
        default_factory=lambda: os.environ.get("OPENMONTAGE_ALLOW_NO_AUTH", "").strip() in ("1", "true", "yes")
    )

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_keys)

    @property
    def operator_auth_enabled(self) -> bool:
        # Human login is active only once the portal wiring is complete.
        return bool(self.titanium_portal_url and self.titanium_app_id and self.titanium_return_url)

    def validate_boot(self) -> None:
        """Fail closed: never come up publicly reachable with auth disabled.

        An unset OPENMONTAGE_API_KEYS used to serve every route — including the
        agent-credential routes — with no auth. Now that only happens on a
        loopback bind or with an explicit dev opt-in.
        """
        if self.auth_enabled:
            return
        loopback = self.host in ("127.0.0.1", "localhost", "::1")
        if loopback or self.allow_no_auth:
            return
        raise RuntimeError(
            "refusing to start: OPENMONTAGE_API_KEYS is empty and the service is "
            f"bound to {self.host} (public). Set OPENMONTAGE_API_KEYS, or set "
            "OPENMONTAGE_ALLOW_NO_AUTH=1 to explicitly run without auth (dev only)."
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.jobs_dir.mkdir(parents=True, exist_ok=True)
        _settings.projects_dir.mkdir(parents=True, exist_ok=True)
    return _settings
