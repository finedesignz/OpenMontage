"""JobManager: lifecycle, concurrency, and result collection.

Holds an asyncio semaphore (max_concurrency) and one background task per job.
Jobs are persisted via JobStore so a redeploy doesn't lose history; in-flight
jobs interrupted by a restart are reconciled to `failed` on boot (the child
process does not survive the container).
"""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime, timezone

from .config import Settings
from .models import Artifact, JobRecord, JobResult, JobStatus
from .runner import AgentRun
from .store import JobStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (base[:48] or "video").rstrip("-")


class JobManager:
    def __init__(self, settings: Settings):
        self._s = settings
        self._store = JobStore(settings.jobs_dir)
        self._sem = asyncio.Semaphore(settings.max_concurrency)
        self._tasks: dict[str, asyncio.Task] = {}
        self._runs: dict[str, AgentRun] = {}
        self._reconcile_orphans()

    def _reconcile_orphans(self) -> None:
        # Any job left running/queued from a previous process is dead.
        for rec in self._store.list(limit=10_000)[0]:
            if rec.status in {JobStatus.running, JobStatus.queued}:
                rec.status = JobStatus.failed
                rec.error = "interrupted by server restart"
                rec.updated_at = _now()
                self._store.put(rec)

    # ---- public API --------------------------------------------------------

    def create(self, prompt: str, pipeline: str | None, budget_usd: float | None, metadata: dict) -> JobRecord:
        job_id = uuid.uuid4().hex
        slug = f"{_slugify(prompt)}-{job_id[:8]}"
        rec = JobRecord(
            job_id=job_id,
            status=JobStatus.queued,
            prompt=prompt,
            pipeline=pipeline,
            project_slug=slug,
            created_at=_now(),
            updated_at=_now(),
            budget_usd=budget_usd or self._s.budget_usd,
            metadata=metadata,
        )
        self._store.put(rec)
        self._tasks[job_id] = asyncio.create_task(self._run(job_id))
        return rec

    def get(self, job_id: str) -> JobRecord | None:
        return self._store.get(job_id)

    def list(self, status: str | None, limit: int, offset: int):
        return self._store.list(status=status, limit=limit, offset=offset)

    async def cancel(self, job_id: str) -> JobRecord | None:
        rec = self._store.get(job_id)
        if not rec or rec.status.terminal:
            return rec
        run = self._runs.get(job_id)
        if run:
            await run.cancel()
        task = self._tasks.get(job_id)
        if task:
            task.cancel()
        rec = self._store.get(job_id) or rec
        rec.status = JobStatus.cancelled
        rec.error = rec.error or "cancelled by request"
        rec.finished_at = _now()
        rec.updated_at = _now()
        self._store.put(rec)
        return rec

    def result(self, job_id: str) -> JobResult | None:
        rec = self._store.get(job_id)
        if not rec:
            return None
        artifacts = self._collect_artifacts(rec)
        final = next((a for a in artifacts if a.kind == "render" and a.name == "final.mp4"), None)
        return JobResult(
            job_id=job_id,
            status=rec.status,
            final_video=final,
            artifacts=artifacts,
            cost_usd=rec.cost_usd,
            error=rec.error,
        )

    @property
    def active_count(self) -> int:
        return sum(1 for t in self._tasks.values() if not t.done())

    # ---- internals ---------------------------------------------------------

    def _project_dir(self, rec: JobRecord):
        return self._s.projects_dir / rec.project_slug

    def _update(self, job_id: str, **fields) -> None:
        rec = self._store.get(job_id)
        if not rec:
            return
        for k, v in fields.items():
            setattr(rec, k, v)
        rec.updated_at = _now()
        self._store.put(rec)

    async def _run(self, job_id: str) -> None:
        async with self._sem:
            rec = self._store.get(job_id)
            if not rec or rec.status == JobStatus.cancelled:
                return
            self._update(job_id, status=JobStatus.running, started_at=_now())

            def on_progress(stage: str, note: str) -> None:
                self._update(job_id, stage=stage, progress_note=note)

            run = AgentRun(self._s, on_progress)
            self._runs[job_id] = run
            try:
                exit_code = await run.execute(
                    rec.prompt, rec.project_slug, rec.pipeline, rec.budget_usd
                )
            except asyncio.CancelledError:
                self._update(job_id, status=JobStatus.cancelled, finished_at=_now())
                return
            except Exception as exc:  # noqa: BLE001 — surface any runner failure to the caller
                self._update(
                    job_id, status=JobStatus.failed, error=f"runner error: {exc}", finished_at=_now()
                )
                return
            finally:
                self._runs.pop(job_id, None)

            cost = self._read_cost(rec)
            final = self._final_video_path(rec)
            if exit_code == 0 and final is not None:
                self._update(
                    job_id,
                    status=JobStatus.completed,
                    exit_code=exit_code,
                    cost_usd=cost,
                    finished_at=_now(),
                    stage="completed",
                )
            else:
                reason = (
                    f"agent exited {exit_code} without producing renders/final.mp4"
                    if exit_code == 0
                    else f"agent exited with code {exit_code}"
                )
                # Without the agent's own words, a bare exit code sends whoever
                # debugs this into the container to find a one-line refusal.
                if run.stderr_tail:
                    reason = f"{reason}: {run.stderr_tail[:600]}"
                self._update(
                    job_id,
                    status=JobStatus.failed,
                    exit_code=exit_code,
                    cost_usd=cost,
                    error=reason,
                    finished_at=_now(),
                )

    def _final_video_path(self, rec: JobRecord):
        p = self._project_dir(rec) / "renders" / "final.mp4"
        return p if p.exists() and p.stat().st_size > 0 else None

    def _read_cost(self, rec: JobRecord) -> float | None:
        # cost_log.json is written by the app's CostTracker; location varies by
        # how the agent wired it. Search the project tree, best-effort.
        import json

        pdir = self._project_dir(rec)
        if not pdir.exists():
            return None
        for log in pdir.rglob("cost_log.json"):
            try:
                data = json.loads(log.read_text(encoding="utf-8"))
                # Prefer the tracker's canonical running total (present even at $0).
                if isinstance(data, dict) and "budget_spent_usd" in data:
                    return round(float(data["budget_spent_usd"]), 4)
                entries = data if isinstance(data, list) else data.get("entries", [])
                total = sum(
                    float(e.get("actual_usd") or e.get("reserved_usd") or 0.0)
                    for e in entries
                    if isinstance(e, dict)
                )
                return round(total, 4)
            except Exception:
                continue
        return None

    def _collect_artifacts(self, rec: JobRecord) -> list[Artifact]:
        pdir = self._project_dir(rec)
        if not pdir.exists():
            return []
        out: list[Artifact] = []
        for f in sorted(pdir.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(self._s.repo_root).as_posix()
            try:
                size = f.stat().st_size
            except OSError:
                continue
            if "renders" in f.parts and f.suffix == ".mp4":
                kind = "render"
            elif f.suffix == ".json":
                kind = "artifact"
            else:
                kind = "asset"
            out.append(Artifact(name=f.name, path=rel, size_bytes=size, kind=kind))
        return out
