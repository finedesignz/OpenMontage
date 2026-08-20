"""Fetch caller-supplied typed source inputs into a job's workspace.

A server-to-server caller (e.g. aiscreenrecorder) has no shared filesystem
with OpenMontage's `projects/` volume, so `CreateJobRequest.inputs` lets it
hand OpenMontage remote media URLs instead. Before the agent run starts we
download each input into the job workspace and write a manifest the agent
prompt points at, so `real_capture` mode can consume pre-supplied footage
instead of assuming a human already dropped files into `projects/`.

Fetch is deliberately defensive — this is unauthenticated-by-URL, caller-
controlled input reaching the server's filesystem:
  - https:// only (also enforced at the model layer; re-checked here in case
    a future caller of fetch_inputs() skips validation).
  - Per-file size cap enforced while streaming (not just via Content-Length,
    which a server can lie about).
  - Fetch timeout.
  - Path containment: the destination path is resolved and checked with
    Path.is_relative_to against the resolved workspace dir, same pattern as
    the artifact-download containment fix in 8a29eb6 (str-prefix containment
    is bypassable; symlinks are rejected).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import httpx

from .config import Settings
from .models import _ROLE_RE, SourceInput


class InputFetchError(Exception):
    """A typed source input could not be safely fetched. Callers should treat
    this as a hard job failure — never silently skip a requested input."""


@dataclass(frozen=True)
class FetchedInput:
    role: str
    path: str  # repo-relative, for the manifest and for Artifact reporting
    content_type: str | None
    size_bytes: int


def _dest_path(settings: Settings, project_slug: str, role: str, url: str) -> Path:
    # Derive an extension from the URL path, if any, so downstream tools that
    # sniff by suffix (ffprobe, playwright import, etc.) still work.
    from urllib.parse import urlsplit

    suffix = Path(urlsplit(url).path).suffix
    if not suffix or len(suffix) > 10 or "/" in suffix:
        suffix = ""
    inputs_dir = settings.projects_dir / project_slug / "inputs"
    return inputs_dir / f"{role}{suffix}"


async def fetch_inputs(
    settings: Settings, project_slug: str, inputs: list[SourceInput]
) -> list[FetchedInput]:
    """Download every input into projects/<slug>/inputs/ and write manifest.json.

    Raises InputFetchError on the first failure — a job that asked for source
    media it never got must fail loudly, not silently proceed prompt-only.
    """
    if not inputs:
        return []

    inputs_dir = settings.projects_dir / project_slug / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    # Containment is scoped to THIS job's own inputs dir, not the whole
    # projects/ tree — otherwise a crafted role could still land inside a
    # sibling job's directory and pass an "is it under projects/" check.
    workspace_root = inputs_dir.resolve()

    fetched: list[FetchedInput] = []
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=settings.input_fetch_timeout_seconds
    ) as client:
        for item in inputs:
            if not item.url.lower().startswith("https://"):
                raise InputFetchError(f"input '{item.role}': url must be https://")
            # Re-validate role shape independently of SourceInput's own
            # validator — defense in depth against a caller that reaches
            # this function with a model built via model_construct() or
            # otherwise bypassing pydantic validation.
            if not _ROLE_RE.match(item.role):
                raise InputFetchError(f"input role '{item.role}': must be 1-64 chars of [a-zA-Z0-9_-]")

            dest = _dest_path(settings, project_slug, item.role, item.url)
            real_dest = dest.resolve()
            # Path containment: resolved destination must stay inside the
            # resolved job inputs dir (mirrors the artifact-download fix in
            # 8a29eb6 — is_relative_to on resolved paths, not str prefix).
            if not real_dest.is_relative_to(workspace_root):
                raise InputFetchError(f"input '{item.role}': destination escapes workspace")
            if dest.exists() and dest.is_symlink():
                raise InputFetchError(f"input '{item.role}': refusing to write through a symlink")

            tmp = dest.with_suffix(dest.suffix + ".part")
            if tmp.exists() and tmp.is_symlink():
                raise InputFetchError(f"input '{item.role}': refusing to write through a symlink")

            written = 0
            try:
                async with client.stream("GET", item.url) as resp:
                    if resp.status_code >= 400:
                        raise InputFetchError(
                            f"input '{item.role}': fetch failed with HTTP {resp.status_code}"
                        )
                    # Redirects are followed by httpx; reject if they left https.
                    final_url = str(resp.url)
                    if not final_url.lower().startswith("https://"):
                        raise InputFetchError(
                            f"input '{item.role}': redirected off https ({final_url})"
                        )
                    content_length = resp.headers.get("content-length")
                    if content_length is not None and int(content_length) > settings.input_max_bytes:
                        raise InputFetchError(
                            f"input '{item.role}': declared size exceeds "
                            f"{settings.input_max_bytes} byte cap"
                        )
                    try:
                        with open(tmp, "wb") as f:
                            async for chunk in resp.aiter_bytes():
                                written += len(chunk)
                                if written > settings.input_max_bytes:
                                    raise InputFetchError(
                                        f"input '{item.role}': exceeded "
                                        f"{settings.input_max_bytes} byte cap while streaming"
                                    )
                                f.write(chunk)
                    except BaseException:
                        tmp.unlink(missing_ok=True)
                        raise
                    tmp.replace(dest)
            except httpx.TimeoutException as exc:
                raise InputFetchError(f"input '{item.role}': fetch timed out") from exc
            except httpx.HTTPError as exc:
                raise InputFetchError(f"input '{item.role}': fetch error: {exc}") from exc

            rel = real_dest.relative_to(settings.repo_root.resolve()).as_posix()
            fetched.append(
                FetchedInput(
                    role=item.role,
                    path=rel,
                    content_type=item.content_type,
                    size_bytes=written,
                )
            )

    manifest = {
        "version": 1,
        "inputs": [
            {
                "role": f.role,
                "path": f.path,
                "content_type": f.content_type,
                "size_bytes": f.size_bytes,
            }
            for f in fetched
        ],
    }
    manifest_path = inputs_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return fetched
