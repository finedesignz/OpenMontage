"""Pydantic request/response models and the job record schema."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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


class CreateJobRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Plain-language production brief.")
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
