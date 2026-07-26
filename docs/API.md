# OpenMontage HTTP API

An async job API that wraps the agent-driven production pipeline so apps and
agents (Edge AIOS, Claude, an MCP server) can request videos over HTTP instead
of driving the repo from a coding assistant.

## Why it works this way

OpenMontage has **no orchestrator in code** — the LLM agent *is* the
orchestrator (see [`AGENT_GUIDE.md`](../AGENT_GUIDE.md), Rule Zero). So the API
does **not** call tools directly. Instead, each job launches a **headless Claude
Code agent inside the container**, which reads the skills and drives the
pipeline exactly as it would locally. The API is a job queue + trigger +
artifact retrieval around that agent run.

```
caller ──HTTP──▶ OpenMontage API ──spawns──▶ `claude -p` (headless, in repo)
                       │                              │ reads skills, runs pipeline
                       │                              ▼
                       └──◀── poll status ──── projects/<slug>/renders/final.mp4
```

This keeps the "intelligence in the skills" guarantee intact. A deterministic
Python state machine calling tools directly would be faster but would throw away
research, scored provider selection, and creative direction — and violate Rule
Zero.

## Endpoints

All `/v1/*` routes require an API key when `OPENMONTAGE_API_KEYS` is set
(`X-API-Key: <key>` or `Authorization: Bearer <key>`). `/health` is open.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness/readiness (`{status, version, active_jobs}`) |
| `GET` | `/openapi.json`, `/docs` | OpenAPI schema + Swagger UI |
| `POST` | `/v1/jobs` | Submit a production brief → `202` + job record |
| `GET` | `/v1/jobs` | List jobs (`?status=&limit=&offset=`) |
| `GET` | `/v1/jobs/{id}` | Job status, stage, progress, cost, error |
| `GET` | `/v1/jobs/{id}/result` | Final video + artifact manifest |
| `GET` | `/v1/jobs/{id}/artifacts/{name}` | Download a render/artifact |
| `POST` | `/v1/jobs/{id}/cancel` | Cancel a running job |
| `GET` | `/v1/pipelines` | Available pipelines |
| `GET` | `/v1/capabilities` | Provider/capability menu (preflight) |
| `GET` | `/setup` | Page to authorize the agent (paste a subscription token) |
| `GET` | `/v1/auth/status` | Is the agent authorized? (open — reveals no secret) |
| `POST` | `/v1/auth/token` | Store a subscription token (verified before it is saved) |
| `POST` | `/v1/auth/verify` | Re-check the stored token against Anthropic |
| `DELETE` | `/v1/auth/token` | Forget the stored token |

## Authorizing the agent

Every render is driven by a headless Claude Code agent inside the container, and
it needs credentials of its own — separate from the API key callers use to reach
this service. **The only supported credential is a Claude subscription token.**
Metered `sk-ant-...` API keys are not a fallback: the runner strips
`ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, and `ANTHROPIC_AUTH_TOKEN` from the
agent's environment, so a stray key can never silently bill per token.

1. On any machine already logged in to Claude Code, run `claude setup-token`.
2. Open `https://<your-domain>/setup`, enter an `OPENMONTAGE_API_KEYS` value and
   paste the token.
3. The API runs one real agent turn to prove the token authenticates, then
   persists it to the `/app/jobs` volume — so it survives redeploys and restarts.

`GET /health` reports `agent_authorized`; until it is `true`, every job fails
fast with a message pointing at `/setup`. `POST /v1/auth/verify` re-checks a
stored token's liveness at any time (tokens are long-lived but not eternal).

### Job lifecycle

`queued → running → completed | failed | cancelled`. Terminal states are
`completed`, `failed`, `cancelled` — poll `GET /v1/jobs/{id}` until terminal,
then `GET /v1/jobs/{id}/result`. (Same shape as the `agentsrecon` MCP server's
`scrape_async` / `get_job` pattern, so an MCP wrapper is a thin pass-through.)

A job is **completed** only when the agent exits `0` **and**
`projects/<slug>/renders/final.mp4` exists and is non-empty. Agent narration is
never trusted as proof of success.

### Example

```bash
# submit
curl -sX POST https://openmontage.example.com/v1/jobs \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"prompt":"45s animated explainer about why the sky is blue","pipeline":"animated-explainer"}'
# => {"job_id":"ab12...", "status":"queued", ...}

# poll
curl -s https://openmontage.example.com/v1/jobs/ab12... -H "X-API-Key: $KEY"

# fetch result + download
curl -s https://openmontage.example.com/v1/jobs/ab12.../result -H "X-API-Key: $KEY"
curl -sO https://openmontage.example.com/v1/jobs/ab12.../artifacts/final.mp4 -H "X-API-Key: $KEY"
```

## Configuration (environment)

| Var | Default | Purpose |
|-----|---------|---------|
| `OPENMONTAGE_API_KEYS` | _(none)_ | Comma-separated bearer keys. **Empty = auth disabled** (dev only). |
| `PORT` / `HOST` | `8080` / `0.0.0.0` | Listen address. |
| `OPENMONTAGE_MAX_CONCURRENCY` | `2` | Concurrent production jobs. |
| `OPENMONTAGE_JOB_TIMEOUT` | `3600` | Per-job wall-clock ceiling (seconds). |
| `OPENMONTAGE_BUDGET_USD` | `10` | Per-job provider spend cap handed to the agent. |
| `OPENMONTAGE_AGENT_MODEL` | _(CLI default)_ | Override the agent model. |
| `OPENMONTAGE_AGENT_MAX_TURNS` | `400` | Agent turn ceiling. |
| `OPENMONTAGE_CLAUDE_BIN` | `claude` | Path to the Claude Code CLI. |
| provider keys | _(optional)_ | `FAL_KEY`, `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, … — read by the tools, same as CLI mode. |

## Run locally

```bash
pip install -r requirements.txt -r requirements-api.txt
uvicorn api.main:app --reload --port 8080
# open http://localhost:8080/docs
```

Until the agent is authorized (see above) jobs fail fast at the launch step — but
`/health`, `/v1/pipelines`, `/setup`, and `/docs` work for wiring and tests.

## Deploy on Coolify

1. New resource → **Dockerfile** build, repo = OpenMontage.
2. Dockerfile location: `Dockerfile.api`. Base directory: `/`.
3. Port: `8080`. Healthcheck path: `/health`.
4. Env vars: `OPENMONTAGE_API_KEYS`, plus any provider keys you want enabled
   (`FAL_KEY`, `OPENAI_API_KEY`, …). Do **not** set `ANTHROPIC_API_KEY` or
   `ANTHROPIC_BASE_URL` — the agent runs on the subscription token instead.
5. **Persistent volumes:** mount `/app/jobs` and `/app/projects` so job history,
   renders, *and the agent's subscription token* survive redeploys. Without the
   `/app/jobs` volume you must re-authorize at `/setup` after every deploy.
6. Domain → `openmontage.<your-domain>`; verify `GET /health` returns `200`.
7. Visit `/setup` and paste a `claude setup-token` token. `/health` should then
   report `"agent_authorized": true`.

## Notes & limits

- **Single web process, N job slots.** Job state lives in-memory + on disk; run
  one web replica and scale via `OPENMONTAGE_MAX_CONCURRENCY`, not replicas. For
  multi-replica scale-out, replace `api/store.py` with a Postgres-backed store
  (the `JobManager` depends only on that interface).
- **Cost/security:** every job runs an autonomous agent that can spend on
  provider APIs up to the budget cap. Keep `OPENMONTAGE_API_KEYS` set in any
  non-local deployment and put the service behind your gateway.
- **Jobs interrupted by a restart** are reconciled to `failed` on boot (the
  child agent process does not survive the container).
