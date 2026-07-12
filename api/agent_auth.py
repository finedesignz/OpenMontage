"""Agent credential store.

The headless agent (Claude Code CLI) needs its own credentials, separate from
the API key callers use to reach this service. There is exactly one supported
source: a Claude subscription OAuth token, generated with `claude setup-token`
on a machine already logged in, then pasted into the /setup page. It is
persisted to the jobs volume so it survives redeploys and restarts, and exported
to each agent subprocess as CLAUDE_CODE_OAUTH_TOKEN.

Metered `sk-ant-...` API keys are deliberately NOT a fallback — this service
bills against the subscription, and a stray ANTHROPIC_API_KEY in the environment
would silently start charging per token. The runner strips it.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Tokens from `claude setup-token` carry this prefix. Checking it turns a paste
# of the wrong string (an API key, a session id) into an error at /setup rather
# than a failed job an hour later.
TOKEN_PREFIX = "sk-ant-oat"


@dataclass(frozen=True)
class AgentAuth:
    source: str  # "oauth_token" | "none"
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
        if not token.startswith(TOKEN_PREFIX):
            raise ValueError(
                f"that does not look like a subscription token (expected it to start "
                f"with '{TOKEN_PREFIX}') — generate one with `claude setup-token`"
            )
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
        if not stored:
            return AgentAuth(source="none", env={})
        token, updated = stored
        return AgentAuth(
            source="oauth_token",
            env={"CLAUDE_CODE_OAUTH_TOKEN": token},
            updated_at=updated,
        )

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


def verify_token(claude_bin: str, token: str, timeout: int = 90) -> tuple[bool, str]:
    """Prove a token actually authenticates, by running the smallest real agent turn.

    A token that merely *looks* right still fails an hour into a render. One
    cheap round trip here turns that into an error the operator sees while they
    still have the /setup page open.
    """
    env = dict(os.environ)
    for shadow in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"):
        env.pop(shadow, None)
    env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    env["CI"] = "1"

    try:
        proc = subprocess.run(
            [claude_bin, "-p", "Reply with the single word OK.", "--max-turns", "3"],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"verification timed out after {timeout}s"
    except OSError as exc:  # missing binary, not executable, bad interpreter
        return False, f"could not run the agent binary ({claude_bin}): {exc}"

    if proc.returncode == 0:
        return True, "token accepted by Anthropic"

    output = f"{proc.stdout}\n{proc.stderr}".strip()
    # A turn-limit exit is not an auth failure: the request reached Anthropic and
    # the model answered. Only a credential complaint means the token is bad.
    if "max turns" in output.lower():
        return True, "token accepted by Anthropic"
    detail = output.splitlines()
    return False, detail[-1][:300] if detail else f"agent exited with code {proc.returncode}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
