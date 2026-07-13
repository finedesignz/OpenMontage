"""FastAPI application — the OpenMontage production API.

Async job model (submit -> poll -> fetch), matching the agentsrecon job pattern
so the MCP wrapper is a thin pass-through:

    POST   /v1/jobs                 submit a production brief -> {job_id}
    GET    /v1/jobs                 list jobs (filter by status)
    GET    /v1/jobs/{id}            job status + progress + cost
    GET    /v1/jobs/{id}/result     final video + artifact manifest
    GET    /v1/jobs/{id}/artifacts/{name}  download a render/artifact
    POST   /v1/jobs/{id}/cancel     cancel a running job
    GET    /v1/pipelines            available pipelines
    GET    /v1/capabilities         provider/capability menu (preflight)
    GET    /health                  liveness + readiness
    GET    /openapi.json , /docs    auto-generated (docs contract)
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import yaml
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse

from .agent_auth import TOKEN_PREFIX, AgentAuthStore, verify_token
from .auth import require_api_key
from .config import get_settings
from .jobs import JobManager
from .models import (
    AgentAuthStatus,
    CreateJobRequest,
    HealthResponse,
    JobList,
    JobRecord,
    JobResult,
    PipelineInfo,
    SetTokenRequest,
)
from .setup_page import SETUP_HTML

API_VERSION = "0.1.0"


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_boot()  # fail closed on a public bind with no auth configured

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.jobs = JobManager(settings)
        yield

    app = FastAPI(
        title="OpenMontage API",
        version=API_VERSION,
        description="Agent-driven video production as an async job service.",
        lifespan=lifespan,
    )

    # ---- health (no auth) --------------------------------------------------

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    async def health() -> HealthResponse:
        jm: JobManager | None = getattr(app.state, "jobs", None)
        return HealthResponse(
            version=API_VERSION,
            agent_runtime=settings.claude_bin,
            active_jobs=jm.active_count if jm else 0,
            agent_authorized=auth_store.load().configured,
        )

    @app.get("/", tags=["meta"])
    async def root() -> dict:
        return {"service": "openmontage", "version": API_VERSION, "docs": "/docs", "setup": "/setup"}

    # ---- agent authorization -----------------------------------------------
    # The headless agent needs credentials of its own. /setup lets an operator
    # paste a Claude subscription token (from `claude setup-token`) into the
    # running container without a redeploy.

    auth_store = AgentAuthStore(settings.jobs_dir)

    def _status() -> AgentAuthStatus:
        auth = auth_store.load()
        return AgentAuthStatus(
            configured=auth.configured, source=auth.source, updated_at=auth.updated_at
        )

    @app.get("/setup", response_class=HTMLResponse, include_in_schema=False)
    async def setup_page() -> HTMLResponse:
        return HTMLResponse(SETUP_HTML)

    # Unauthenticated on purpose: it reveals only whether the agent can run, and
    # the page must render it before the operator has typed a key.
    @app.get("/v1/auth/status", response_model=AgentAuthStatus, tags=["auth"])
    async def auth_status() -> AgentAuthStatus:
        return _status()

    @app.post("/v1/auth/token", response_model=AgentAuthStatus, tags=["auth"], dependencies=[Depends(require_api_key)])
    async def set_agent_token(req: SetTokenRequest) -> AgentAuthStatus:
        token = req.token.strip()
        if not token.startswith(TOKEN_PREFIX):
            raise HTTPException(
                400,
                f"that does not look like a subscription token (expected it to start with "
                f"'{TOKEN_PREFIX}') — generate one with `claude setup-token`",
            )
        # Prove the token works before persisting it, so a bad paste fails here
        # rather than silently breaking every future job.
        ok, detail = await asyncio.to_thread(verify_token, settings.claude_bin, token)
        if not ok:
            raise HTTPException(400, f"token rejected: {detail}")
        try:
            auth_store.set_token(token)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        return _status()

    @app.post("/v1/auth/verify", tags=["auth"], dependencies=[Depends(require_api_key)])
    async def verify_agent_token() -> dict:
        """Re-check the stored token against Anthropic — is the agent still connected?"""
        auth = auth_store.load()
        if not auth.configured:
            raise HTTPException(409, "no token stored — paste one at /setup")
        ok, detail = await asyncio.to_thread(
            verify_token, settings.claude_bin, auth.env["CLAUDE_CODE_OAUTH_TOKEN"]
        )
        return {"valid": ok, "detail": detail, "updated_at": auth.updated_at}

    @app.delete("/v1/auth/token", response_model=AgentAuthStatus, tags=["auth"], dependencies=[Depends(require_api_key)])
    async def clear_agent_token() -> AgentAuthStatus:
        auth_store.clear()
        return _status()

    # ---- jobs --------------------------------------------------------------

    @app.post("/v1/jobs", response_model=JobRecord, status_code=202, tags=["jobs"], dependencies=[Depends(require_api_key)])
    async def create_job(req: CreateJobRequest) -> JobRecord:
        jm: JobManager = app.state.jobs
        return jm.create(req.prompt, req.pipeline, req.budget_usd, req.metadata)

    @app.get("/v1/jobs", response_model=JobList, tags=["jobs"], dependencies=[Depends(require_api_key)])
    async def list_jobs(
        status: str | None = Query(None, description="Filter: queued|running|completed|failed|cancelled"),
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> JobList:
        jm: JobManager = app.state.jobs
        records, total = jm.list(status, limit, offset)
        return JobList(jobs=records, total=total)

    @app.get("/v1/jobs/{job_id}", response_model=JobRecord, tags=["jobs"], dependencies=[Depends(require_api_key)])
    async def get_job(job_id: str) -> JobRecord:
        jm: JobManager = app.state.jobs
        rec = jm.get(job_id)
        if not rec:
            raise HTTPException(404, "job not found")
        return rec

    @app.get("/v1/jobs/{job_id}/result", response_model=JobResult, tags=["jobs"], dependencies=[Depends(require_api_key)])
    async def get_result(job_id: str) -> JobResult:
        jm: JobManager = app.state.jobs
        res = jm.result(job_id)
        if not res:
            raise HTTPException(404, "job not found")
        return res

    @app.get("/v1/jobs/{job_id}/artifacts/{name}", tags=["jobs"], dependencies=[Depends(require_api_key)])
    async def download_artifact(job_id: str, name: str) -> FileResponse:
        jm: JobManager = app.state.jobs
        res = jm.result(job_id)
        if not res:
            raise HTTPException(404, "job not found")
        match = next((a for a in res.artifacts if a.name == name), None)
        if not match:
            raise HTTPException(404, "artifact not found")
        abs_path = (settings.repo_root / match.path).resolve()
        # Defence in depth: never serve outside the repo's projects tree.
        if not str(abs_path).startswith(str(settings.projects_dir.resolve())):
            raise HTTPException(403, "forbidden path")
        if not abs_path.exists():
            raise HTTPException(410, "artifact no longer on disk")
        return FileResponse(str(abs_path), filename=name)

    @app.post("/v1/jobs/{job_id}/cancel", response_model=JobRecord, tags=["jobs"], dependencies=[Depends(require_api_key)])
    async def cancel_job(job_id: str) -> JobRecord:
        jm: JobManager = app.state.jobs
        rec = await jm.cancel(job_id)
        if not rec:
            raise HTTPException(404, "job not found")
        return rec

    # ---- discovery ---------------------------------------------------------

    @app.get("/v1/pipelines", response_model=list[PipelineInfo], tags=["discovery"], dependencies=[Depends(require_api_key)])
    async def list_pipelines() -> list[PipelineInfo]:
        out: list[PipelineInfo] = []
        for f in sorted((settings.repo_root / "pipeline_defs").glob("*.yaml")):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            out.append(
                PipelineInfo(
                    name=data.get("name") or f.stem,
                    best_for=data.get("best_for") or data.get("description"),
                    stability=data.get("stability") or data.get("status"),
                )
            )
        return out

    @app.get("/v1/capabilities", tags=["discovery"], dependencies=[Depends(require_api_key)])
    async def capabilities() -> dict:
        def _probe() -> dict:
            from tools.tool_registry import registry

            registry.discover()
            return registry.provider_menu_summary()

        try:
            return await asyncio.to_thread(_probe)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(503, f"capability probe failed: {exc}")

    return app


app = create_app()
