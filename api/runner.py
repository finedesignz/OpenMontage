"""Headless agent runner.

Each job drives one production run by launching the Claude Code CLI in
non-interactive (`-p`) mode inside the repo. This is the only design that
honours OpenMontage's contract: the intelligence lives in the skills, and an
agent must read them to drive the pipeline. We do NOT re-implement orchestration
in Python (that would violate Rule Zero in AGENT_GUIDE.md).

The runner is intentionally defensive about the agent's stdout: it parses the
`stream-json` event log best-effort for progress signals, but correctness of a
job is judged structurally — process exit code plus the presence of a rendered
`final.mp4` — not by trusting the agent's narration.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
from collections.abc import Callable

from .config import Settings

ProgressCb = Callable[[str, str], None]  # (stage, note) -> None


def build_prompt(prompt: str, project_slug: str, pipeline: str | None, budget_usd: float) -> str:
    """Compose the autonomous production brief handed to the headless agent."""
    pipeline_line = (
        f"- Use the `{pipeline}` pipeline.\n"
        if pipeline
        else "- Select the most appropriate pipeline yourself.\n"
    )
    return (
        "You are running HEADLESS in an automated service. There is NO human to "
        "approve checkpoints — you must run the entire production autonomously, "
        "end to end, without pausing for confirmation.\n\n"
        "Follow AGENT_GUIDE.md and Rule Zero: go through the pipeline system, read "
        "the stage director skills, read Layer 3 skills before calling generation "
        "tools. Do not write ad-hoc scripts that bypass the pipeline.\n\n"
        "AUTONOMOUS-MODE OVERRIDES (these replace the human-approval defaults):\n"
        f"- Write ALL outputs under the project directory: projects/{project_slug}/\n"
        "  The final deliverable MUST be projects/"
        f"{project_slug}/renders/final.mp4\n"
        f"- Treat every stage's human_approval_default as auto-approve. Self-review, "
        "then proceed. Do not stop to ask the user anything.\n"
        f"- Hard budget cap: ${budget_usd:.2f} total. Configure the cost tracker with "
        "this cap in 'cap' mode. If a path would exceed it, choose the best "
        "available cheaper path rather than stopping.\n"
        "- When both composition runtimes are available, pick one with a logged "
        "render_runtime_selection decision (you cannot ask the user) and proceed.\n"
        "- If a blocker is truly unrecoverable, stop and explain it clearly in your "
        "final message; do not loop.\n\n"
        f"{pipeline_line}"
        "\nPRODUCTION BRIEF:\n"
        f"{prompt}\n"
    )


class AgentRun:
    """Owns one headless agent subprocess for the lifetime of a job."""

    def __init__(self, settings: Settings, on_progress: ProgressCb):
        self._s = settings
        self._on_progress = on_progress
        self._proc: asyncio.subprocess.Process | None = None

    async def execute(
        self, prompt: str, project_slug: str, pipeline: str | None, budget_usd: float
    ) -> int:
        agent_prompt = build_prompt(prompt, project_slug, pipeline, budget_usd)

        argv = [
            self._s.claude_bin,
            "-p",
            agent_prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "bypassPermissions",
            "--max-turns",
            str(self._s.agent_max_turns),
        ]
        if self._s.agent_model:
            argv += ["--model", self._s.agent_model]

        env = dict(os.environ)
        env["OPENMONTAGE_BUDGET_USD"] = f"{budget_usd}"
        env.setdefault("CI", "1")  # discourage interactive prompts in child tooling

        self._proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(self._s.repo_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            await asyncio.wait_for(self._pump_stdout(), timeout=self._s.job_timeout_seconds)
            return await self._proc.wait()
        except asyncio.TimeoutError:
            self._on_progress("timeout", f"exceeded {self._s.job_timeout_seconds}s")
            await self._terminate()
            return 124
        except asyncio.CancelledError:
            await self._terminate()
            raise

    async def cancel(self) -> None:
        await self._terminate()

    async def _terminate(self) -> None:
        if self._proc and self._proc.returncode is None:
            try:
                if os.name == "nt":
                    self._proc.terminate()
                else:
                    self._proc.send_signal(signal.SIGTERM)
                await asyncio.wait_for(self._proc.wait(), timeout=10)
            except (asyncio.TimeoutError, ProcessLookupError):
                try:
                    self._proc.kill()
                except ProcessLookupError:
                    pass

    async def _pump_stdout(self) -> None:
        assert self._proc and self._proc.stdout
        async for raw in self._proc.stdout:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            self._scan_event(line)

    def _scan_event(self, line: str) -> None:
        """Best-effort progress extraction from a stream-json line."""
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            return
        etype = evt.get("type")
        if etype == "assistant":
            text = _assistant_text(evt)
            if text:
                self._on_progress("running", text[:280])
        elif etype == "result":
            note = "agent finished" if not evt.get("is_error") else "agent reported error"
            self._on_progress("finalizing", note)


def _assistant_text(evt: dict) -> str:
    msg = evt.get("message") or {}
    parts = msg.get("content") or []
    chunks = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"]
    return " ".join(c for c in chunks if c).strip()
