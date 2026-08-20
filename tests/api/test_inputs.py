"""Tests for api.inputs.fetch_inputs — the typed-source-input downloader.

Network calls are stubbed via httpx.MockTransport (no real HTTP), so these
run offline and deterministically.
"""

from __future__ import annotations

import json

import httpx
import pytest

from api.config import Settings
from api.inputs import InputFetchError, fetch_inputs
from api.models import SourceInput


def _settings(tmp_path, **overrides) -> Settings:
    kwargs = dict(
        repo_root=tmp_path,
        jobs_dir=tmp_path / "jobs",
        projects_dir=tmp_path / "projects",
        input_max_bytes=1024,
        input_fetch_timeout_seconds=5,
    )
    kwargs.update(overrides)
    return Settings(**kwargs)


def _patch_transport(monkeypatch, handler) -> None:
    transport = httpx.MockTransport(handler)

    class _PatchedClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _PatchedClient)


@pytest.mark.asyncio
async def test_fetch_inputs_valid(tmp_path, monkeypatch):
    body = b"fake-mp4-bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-length": str(len(body))})

    _patch_transport(monkeypatch, handler)
    settings = _settings(tmp_path)
    inputs = [SourceInput(role="screen_recording", url="https://example.com/rec.mp4")]

    fetched = await fetch_inputs(settings, "demo-slug", inputs)

    assert len(fetched) == 1
    assert fetched[0].role == "screen_recording"
    assert fetched[0].size_bytes == len(body)
    dest = settings.projects_dir / "demo-slug" / "inputs" / "screen_recording.mp4"
    assert dest.read_bytes() == body

    manifest_path = settings.projects_dir / "demo-slug" / "inputs" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["inputs"][0]["role"] == "screen_recording"
    assert manifest["inputs"][0]["path"].endswith("screen_recording.mp4")


def test_source_input_rejects_non_https():
    with pytest.raises(ValueError):
        SourceInput(role="screen_recording", url="http://example.com/rec.mp4")


@pytest.mark.asyncio
async def test_fetch_inputs_oversize_declared_rejected(tmp_path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 10, headers={"content-length": "999999"})

    _patch_transport(monkeypatch, handler)
    settings = _settings(tmp_path, input_max_bytes=100)
    inputs = [SourceInput(role="screen_recording", url="https://example.com/rec.mp4")]

    with pytest.raises(InputFetchError, match="exceeds"):
        await fetch_inputs(settings, "demo-slug", inputs)


@pytest.mark.asyncio
async def test_fetch_inputs_oversize_while_streaming_rejected(tmp_path, monkeypatch):
    # No (or an understated) content-length header — cap must still be
    # enforced while streaming, not just from the header.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 500)

    _patch_transport(monkeypatch, handler)
    settings = _settings(tmp_path, input_max_bytes=100)
    inputs = [SourceInput(role="screen_recording", url="https://example.com/rec.mp4")]

    with pytest.raises(InputFetchError, match="cap"):
        await fetch_inputs(settings, "demo-slug", inputs)

    # No partial/leftover file should remain in the workspace.
    inputs_dir = settings.projects_dir / "demo-slug" / "inputs"
    leftover = list(inputs_dir.glob("*")) if inputs_dir.exists() else []
    assert not any(f.suffix == ".mp4" for f in leftover)


@pytest.mark.asyncio
async def test_fetch_inputs_bad_role_shape_rejected(tmp_path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x")

    _patch_transport(monkeypatch, handler)
    settings = _settings(tmp_path)

    # Simulate a caller that bypassed model validation (e.g. a future direct
    # call to fetch_inputs) by crafting a SourceInput via model_construct to
    # smuggle a path-escaping role. fetch_inputs re-validates role shape
    # independently of SourceInput's own validator, so this is rejected before
    # any path is even computed.
    escaping = SourceInput.model_construct(role="../../etc/evil", url="https://example.com/x")

    with pytest.raises(InputFetchError, match="must be 1-64 chars"):
        await fetch_inputs(settings, "demo-slug", [escaping])


@pytest.mark.asyncio
async def test_fetch_inputs_path_containment_rejected(tmp_path, monkeypatch):
    # Isolate the path-containment guard itself (belt-and-suspenders behind the
    # role-shape check above): even if a future bug in _dest_path ever computed
    # a destination outside the job's inputs dir, fetch_inputs must still
    # refuse to write there rather than trusting the computed path.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x")

    _patch_transport(monkeypatch, handler)
    settings = _settings(tmp_path)

    import api.inputs as inputs_module

    escaping_path = (settings.projects_dir / ".." / "outside" / "evil.mp4").resolve()
    monkeypatch.setattr(inputs_module, "_dest_path", lambda *a, **kw: escaping_path)

    valid = SourceInput(role="screen_recording", url="https://example.com/x.mp4")

    with pytest.raises(InputFetchError, match="escapes workspace"):
        await fetch_inputs(settings, "demo-slug", [valid])


@pytest.mark.asyncio
async def test_fetch_inputs_http_error_status_rejected(tmp_path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    _patch_transport(monkeypatch, handler)
    settings = _settings(tmp_path)
    inputs = [SourceInput(role="screen_recording", url="https://example.com/missing.mp4")]

    with pytest.raises(InputFetchError, match="HTTP 404"):
        await fetch_inputs(settings, "demo-slug", inputs)


@pytest.mark.asyncio
async def test_fetch_inputs_empty_list_is_noop(tmp_path):
    settings = _settings(tmp_path)
    fetched = await fetch_inputs(settings, "demo-slug", [])
    assert fetched == []
