"""Tests for JobManager's typed-source-input wiring in api.jobs.

The network fetch itself is covered in test_inputs.py; here we verify
JobManager's orchestration: prompt-only jobs stay backward compatible (no
fetch attempted), a fetch failure fails the job loudly instead of silently
falling back to a prompt-only run, and an inputs job fetches before the
agent run starts.
"""

from __future__ import annotations

import asyncio

import pytest

from api.config import Settings
from api.inputs import InputFetchError
from api.jobs import JobManager
from api.models import JobStatus, SourceInput


def _settings(tmp_path) -> Settings:
    return Settings(
        repo_root=tmp_path,
        jobs_dir=tmp_path / "jobs",
        projects_dir=tmp_path / "projects",
        max_concurrency=2,
    )


async def _drain(jm: JobManager, job_id: str, timeout: float = 2.0) -> None:
    task = jm._tasks.get(job_id)
    if task:
        await asyncio.wait_for(task, timeout=timeout)


@pytest.mark.asyncio
async def test_prompt_only_job_never_calls_fetch(tmp_path, monkeypatch):
    calls: list = []

    async def fake_fetch(settings, slug, inputs):
        calls.append((slug, inputs))
        return []

    async def fake_execute(self, prompt, project_slug, pipeline, budget_usd, has_inputs=False):
        assert has_inputs is False
        return 0

    monkeypatch.setattr("api.jobs.AgentRun.execute", fake_execute)

    jm = JobManager(_settings(tmp_path), fetch_inputs_fn=fake_fetch)
    rec = jm.create("a plain prompt", None, None, {})
    await _drain(jm, rec.job_id)

    assert calls == []
    final = jm.get(rec.job_id)
    assert final.status == JobStatus.failed  # no final.mp4 written by the fake run
    assert final.inputs is None


@pytest.mark.asyncio
async def test_inputs_job_fetches_before_agent_run(tmp_path, monkeypatch):
    calls: list = []

    async def fake_fetch(settings, slug, inputs):
        calls.append((slug, [i.role for i in inputs]))
        return []

    async def fake_execute(self, prompt, project_slug, pipeline, budget_usd, has_inputs=False):
        assert has_inputs is True
        # Fetch must have already run by the time execute() is called.
        assert calls, "fetch_inputs should run before AgentRun.execute"
        return 0

    monkeypatch.setattr("api.jobs.AgentRun.execute", fake_execute)

    jm = JobManager(_settings(tmp_path), fetch_inputs_fn=fake_fetch)
    inputs = [SourceInput(role="screen_recording", url="https://example.com/rec.mp4")]
    rec = jm.create("prompt with inputs", None, None, {}, inputs)
    await _drain(jm, rec.job_id)

    assert len(calls) == 1
    assert calls[0][1] == ["screen_recording"]


@pytest.mark.asyncio
async def test_fetch_failure_fails_job_without_running_agent(tmp_path, monkeypatch):
    execute_called = False

    async def fake_fetch(settings, slug, inputs):
        raise InputFetchError("input 'screen_recording': fetch failed with HTTP 404")

    async def fake_execute(self, prompt, project_slug, pipeline, budget_usd, has_inputs=False):
        nonlocal execute_called
        execute_called = True
        return 0

    monkeypatch.setattr("api.jobs.AgentRun.execute", fake_execute)

    jm = JobManager(_settings(tmp_path), fetch_inputs_fn=fake_fetch)
    inputs = [SourceInput(role="screen_recording", url="https://example.com/missing.mp4")]
    rec = jm.create("prompt with inputs", None, None, {}, inputs)
    await _drain(jm, rec.job_id)

    assert execute_called is False
    final = jm.get(rec.job_id)
    assert final.status == JobStatus.failed
    assert "input fetch failed" in final.error
    assert "404" in final.error
