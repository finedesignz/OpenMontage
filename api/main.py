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
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

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
    LoginRequest,
    PipelineInfo,
    SetTokenRequest,
)
from .session import (
    COOKIE_NAME,
    SESSION_TTL_SECONDS,
    PortalClient,
    PortalError,
    SessionManager,
)
from .setup_page import LOGIN_HTML, render_setup

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

    # ---- operator login (Titanium magic-link) ------------------------------
    # /setup and the agent-credential routes are operator actions. When the
    # Titanium portal is wired (operator_auth_enabled), they require a human
    # session; until then they fall back to the machine API key so a partial
    # rollout can't lock the operator out.

    auth_store = AgentAuthStore(settings.jobs_dir)
    session_mgr = SessionManager(settings)
    portal = PortalClient(settings)

    def _require_operator(request: Request) -> None:
        """Gate operator actions: a valid session, or (fallback) the API key."""
        if settings.operator_auth_enabled:
            sess = session_mgr.verify(request.cookies.get(COOKIE_NAME))
            if sess:
                return
        # Machine callers (and the pre-login rollout window) use the API key.
        require_api_key(request.headers.get("x-api-key"), request.headers.get("authorization"))

    def _check_origin(request: Request) -> None:
        # CSRF defence for cookie-authenticated mutations: the session cookie is
        # SameSite=Strict, and we additionally require a same-origin Origin
        # header on state-changing requests. API-key callers send no cookie and
        # are unaffected.
        if not settings.operator_auth_enabled:
            return
        origin = request.headers.get("origin")
        if origin and settings.titanium_return_url:
            allowed = settings.titanium_return_url.split("/auth/")[0]
            if not origin.rstrip("/").startswith(allowed.rstrip("/")):
                raise HTTPException(403, "cross-origin request refused")

    def _status() -> AgentAuthStatus:
        auth = auth_store.load()
        return AgentAuthStatus(
            configured=auth.configured, source=auth.source, updated_at=auth.updated_at
        )

    @app.post("/auth/login", include_in_schema=False)
    async def auth_login(payload: LoginRequest) -> dict:
        if not portal.configured:
            raise HTTPException(503, "operator login is not configured on this deployment")
        email = payload.email.strip().lower()
        if settings.operator_emails and email not in [e.lower() for e in settings.operator_emails]:
            # Do not reveal whether an address is on the allowlist.
            return {"ok": True}
        try:
            await portal.send_magic_link(email)
        except PortalError as exc:
            raise HTTPException(exc.status, exc.detail)
        return {"ok": True}

    @app.get("/auth/callback", include_in_schema=False)
    async def auth_callback(act: str | None = None) -> RedirectResponse:
        if not act:
            raise HTTPException(400, "missing activation token")
        try:
            email = await portal.exchange(act)
        except PortalError as exc:
            raise HTTPException(exc.status, exc.detail)
        if settings.operator_emails and email.lower() not in [e.lower() for e in settings.operator_emails]:
            raise HTTPException(403, "this account is not an authorised operator")
        resp = RedirectResponse("/setup", status_code=302)
        resp.set_cookie(
            COOKIE_NAME,
            session_mgr.issue(email),
            max_age=SESSION_TTL_SECONDS,
            httponly=True,
            secure=True,
            samesite="strict",
            path="/",
        )
        return resp

    @app.post("/auth/logout", include_in_schema=False)
    async def auth_logout() -> RedirectResponse:
        resp = RedirectResponse("/setup", status_code=302)
        resp.delete_cookie(COOKIE_NAME, path="/")
        return resp

    # ---- agent authorization -----------------------------------------------

    @app.get("/setup", response_class=HTMLResponse, include_in_schema=False)
    async def setup_page(request: Request) -> HTMLResponse:
        # Show the login view until the operator has a session; the token view
        # after. When operator auth is not wired, the token view is shown
        # directly (the API-key fallback guards the mutation).
        if settings.operator_auth_enabled:
            sess = session_mgr.verify(request.cookies.get(COOKIE_NAME))
            if not sess:
                return HTMLResponse(LOGIN_HTML)
            return HTMLResponse(render_setup(sess.email))
        return HTMLResponse(render_setup(None))

    @app.get("/v1/auth/session", tags=["auth"], include_in_schema=False)
    async def auth_session(request: Request) -> dict:
        sess = session_mgr.verify(request.cookies.get(COOKIE_NAME)) if settings.operator_auth_enabled else None
        return {
            "login_required": settings.operator_auth_enabled,
            "authenticated": bool(sess) or not settings.operator_auth_enabled,
            "email": sess.email if sess else None,
        }

    # Unauthenticated: reveals only whether the agent can run, and the page must
    # render it before the operator has logged in.
    @app.get("/v1/auth/status", response_model=AgentAuthStatus, tags=["auth"])
    async def auth_status() -> AgentAuthStatus:
        return _status()

    @app.post("/v1/auth/token", response_model=AgentAuthStatus, tags=["auth"])
    async def set_agent_token(req: SetTokenRequest, request: Request) -> AgentAuthStatus:
        _require_operator(request)
        _check_origin(request)
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

    @app.post("/v1/auth/verify", tags=["auth"])
    async def verify_agent_token(request: Request) -> dict:
        """Re-check the stored token against Anthropic — is the agent still connected?"""
        _require_operator(request)
        auth = auth_store.load()
        if not auth.configured:
            raise HTTPException(409, "no token stored — paste one at /setup")
        ok, detail = await asyncio.to_thread(
            verify_token, settings.claude_bin, auth.env["CLAUDE_CODE_OAUTH_TOKEN"]
        )
        return {"valid": ok, "detail": detail, "updated_at": auth.updated_at}

    @app.delete("/v1/auth/token", response_model=AgentAuthStatus, tags=["auth"])
    async def clear_agent_token(request: Request) -> AgentAuthStatus:
        _require_operator(request)
        _check_origin(request)
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
