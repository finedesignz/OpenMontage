"""File-backed job store.

One JSON file per job under `jobs/`. An in-memory dict is the hot cache;
every mutation is written through to disk so jobs survive a container restart
(Coolify redeploys, crashes). This deliberately mirrors OpenMontage's own
"Python = persistence on the filesystem" design and keeps the API a single
stateless-enough container with a mounted volume.

If you later need multi-replica horizontal scaling, swap this class for a
Postgres-backed implementation (DATABASE_URL on Coolify) — the JobManager only
depends on this interface, not on the filesystem.
"""

from __future__ import annotations

import threading
from pathlib import Path

from .models import JobRecord


class JobStore:
    def __init__(self, jobs_dir: Path):
        self._dir = jobs_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._cache: dict[str, JobRecord] = {}
        self._load_all()

    def _path(self, job_id: str) -> Path:
        return self._dir / f"{job_id}.json"

    def _load_all(self) -> None:
        for f in self._dir.glob("*.json"):
            try:
                self._cache[f.stem] = JobRecord.model_validate_json(f.read_text(encoding="utf-8"))
            except Exception:
                # A corrupt record must not take down the whole API on boot.
                continue

    def put(self, record: JobRecord) -> None:
        with self._lock:
            self._cache[record.job_id] = record
            tmp = self._path(record.job_id).with_suffix(".json.tmp")
            tmp.write_text(record.model_dump_json(indent=2), encoding="utf-8")
            tmp.replace(self._path(record.job_id))

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._cache.get(job_id)

    def list(self, status: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[JobRecord], int]:
        with self._lock:
            records = sorted(self._cache.values(), key=lambda r: r.created_at, reverse=True)
        if status:
            records = [r for r in records if r.status.value == status]
        total = len(records)
        return records[offset : offset + limit], total
