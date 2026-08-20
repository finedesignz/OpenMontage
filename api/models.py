"""Pydantic request/response models and the job record schema."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

    @property
    def terminal(self) -> bool:
        return self in {JobStatus.completed, JobStatus.failed, JobStatus.cancelled}


# Terminal-state set the MCP wrapper / pollers can rely on (mirrors agentsrecon).
TERMINAL_STATUSES = {JobStatus.completed.value, JobStatus.failed.value, JobStatus.cancelled.value}


_ROLE_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class SourceInput(BaseModel):
    """A remote media asset the server fetches into the job workspace before the
    agent run. A server-to-server caller (e.g. aiscreenrecorder) has no shared
    filesystem with OpenMontage's `projects/` volume, so this is how it hands
    OpenMontage source footage/audio/assets instead of describing them in prose
    inside `prompt`. Fetching (and its security constraints) lives in api/inputs.py;
    generating narration from this footage remains OpenMontage's own job."""

    role: str = Field(
        ...,
        description="Logical name for this input (e.g. 'screen_recording', 'voiceover', 'logo'). "
        "Used as the filename stem under projects/<slug>/inputs/ and referenced by role in the manifest.",
    )
    url: str = Field(..., min_length=1, max_length=2048, description="HTTPS URL the server will fetch.")
    content_type: str | None = Field(None, max_length=128, description="Optional MIME-type hint.")
    duration_sec: float | None = Field(None, gt=0, description="Optional duration hint (seconds).")

    @field_validator("role")
    @classmethod
    def _role_shape(cls, v: str) -> str:
        if not _ROLE_RE.match(v):
            raise ValueError("role must be 1-64 chars of [a-zA-Z0-9_-]")
        return v

    @field_validator("url")
    @classmethod
    def _https_only(cls, v: str) -> str:
        if not v.lower().startswith("https://"):
            raise ValueError("url must be an https:// URL")
        return v


class CreateJobRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=20000, description="Plain-language production brief.")
    pipeline: str | None = Field(
        None,
        description="Optional pipeline hint (e.g. 'animated-explainer'). If omitted the agent selects one.",
    )
    budget_usd: float | None = Field(
        None, gt=0, description="Override the per-job spend cap (USD). Defaults to server config."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Opaque caller metadata echoed back on the job record."
    )
    inputs: list[SourceInput] | None = Field(
        None,
        max_length=20,
        description="Optional typed source media the server fetches into the job workspace before the "
        "agent runs (e.g. a screen recording URL for the screen-demo pipeline's real_capture mode). "
        "Omit for prompt-only jobs (fully backward compatible).",
    )


class Artifact(BaseModel):
    name: str
    path: str  # repo-relative
    size_bytes: int
    kind: str  # "render" | "artifact" | "asset"


class JobRecord(BaseModel):
    job_id: str
    status: JobStatus
    prompt: str
    pipeline: str | None = None
    project_slug: str
    created_at: str
    updated_at: str
    started_at: str | None = None
    finished_at: str | None = None
    # Progress signal scraped from the agent stream — best-effort, not a contract.
    stage: str | None = None
    progress_note: str | None = None
    cost_usd: float | None = None
    error: str | None = None
    exit_code: int | None = None
    budget_usd: float = 10.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    inputs: list[SourceInput] | None = None

    def public(self) -> "JobRecord":
        return self


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    final_video: Artifact | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
    cost_usd: float | None = None
    error: str | None = None


class JobList(BaseModel):
    jobs: list[JobRecord]
    total: int


class PipelineInfo(BaseModel):
    name: str
    best_for: str | None = None
    stability: str | None = None


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254, description="Operator email for the magic link.")


class SetTokenRequest(BaseModel):
    token: str = Field(
        ...,
        min_length=1,
        description="Claude subscription OAuth token, from `claude setup-token`.",
    )


class AgentAuthStatus(BaseModel):
    configured: bool
    source: str = Field(..., description="oauth_token | api_key | none")
    updated_at: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "openmontage"
    version: str
    agent_runtime: str
    active_jobs: int
    # False => the agent has no credentials and every job will fail. See /setup.
    agent_authorized: bool = False
