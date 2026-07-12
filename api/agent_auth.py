"""Agent credential store.

The headless agent (Claude Code CLI) needs its own credentials, separate from
the API key callers use to reach this service. Two ways to supply them:

1. A Claude subscription OAuth token, generated on a machine with a browser via
   `claude setup-token`, then pasted into the /setup page. Persisted to the jobs
   volume so it survives redeploys, and exported to the agent subprocess as
   CLAUDE_CODE_OAUTH_TOKEN.
2. An `sk-ant-...` API key set as ANTHROPIC_API_KEY in the environment.

The stored token wins over the environment: the operator pasted it more
recently than the container was configured.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class AgentAuth:
    source: str  # "oauth_token" | "api_key" | "none"
    env: dict[str, str]
    updated_at: str | None = None

    @property
    def configured(self) -> bool:
        return self.source != "none"


class AgentAuthStore:
    """One JSON file on the jobs volume holding the pasted OAuth token."""

    def __init__(self, jobs_dir: Path):
        self._path = jobs_dir / "agent_auth.json"

    def set_token(self, token: str) -> AgentAuth:
        token = token.strip()
        if not token:
            raise ValueError("token is empty")
        payload = {"oauth_token": token, "updated_at": _now()}
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(self._path)
        try:
            self._path.chmod(0o600)
        except OSError:
            pass  # non-POSIX filesystem; the volume is not world-readable anyway
        return self.load()

    def clear(self) -> None:
        self._path.unlink(missing_ok=True)

    def load(self) -> AgentAuth:
        stored = self._read()
        if stored:
            token, updated = stored
            # A subscription token authenticates against Anthropic directly; a
            # stale ANTHROPIC_BASE_URL pointing at a gateway would break it.
            return AgentAuth(
                source="oauth_token",
                env={"CLAUDE_CODE_OAUTH_TOKEN": token},
                updated_at=updated,
            )
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if api_key:
            return AgentAuth(source="api_key", env={"ANTHROPIC_API_KEY": api_key})
        return AgentAuth(source="none", env={})

    def _read(self) -> tuple[str, str | None] | None:
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        token = (data.get("oauth_token") or "").strip()
        if not token:
            return None
        return token, data.get("updated_at")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
