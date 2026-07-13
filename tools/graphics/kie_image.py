"""KIE.ai image generation (Nano Banana / gpt-image-1).

KIE is the *fallback* image provider, not the default. The pipeline prefers, in
order: what the Claude CLI agent can decide and compose for free (Remotion,
ffmpeg), then free/local asset tools, and only then a paid generator. Reach for
this when a scene genuinely needs generated imagery that nothing above can draw.

KIE fronts two different APIs, and they do not share a shape:

  nano-banana   -> POST /api/v1/jobs/createTask       -> GET /api/v1/jobs/recordInfo
  gpt-image-1   -> POST /api/v1/gpt4o-image/generate  -> GET /api/v1/gpt4o-image/record-info

Both are async: create a task, poll until it terminates, download the result.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)

BASE_URL = "https://api.kie.ai"
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 300

# KIE's own state vocabulary. Anything not terminal means "keep waiting".
TERMINAL_SUCCESS = {"success", "SUCCESS"}
TERMINAL_FAILURE = {"fail", "FAIL", "failed", "GENERATE_FAILED", "CREATE_TASK_FAILED"}


class KieImage(BaseTool):
    name = "kie_image"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "kie"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC  # async upstream, but we block until done
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []  # stdlib only — no SDK to install
    install_instructions = "Set KIE_API_KEY to your KIE.ai API key (https://kie.ai)."
    agent_skills = ["flux-best-practices"]

    capabilities = ["generate_image", "generate_illustration", "text_to_image"]
    supports = {
        "complex_instructions": True,
        "text_in_image": True,  # via the gpt-image-1 model
        "multiple_outputs": False,
    }
    best_for = [
        "photoreal and illustrative scene imagery (nano-banana)",
        "images containing legible text, logos, UI, infographics (gpt-image-1)",
        "vertical social formats (9:16)",
    ]
    not_good_for = ["offline generation", "zero-budget projects"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "model": {
                "type": "string",
                "enum": ["nano-banana", "gpt-image-1"],
                "default": "nano-banana",
                "description": "nano-banana for scene imagery; gpt-image-1 when the image must contain legible text.",
            },
            "image_size": {
                "type": "string",
                "enum": ["1:1", "9:16", "16:9", "3:2", "2:3", "4:3", "3:4"],
                "default": "9:16",
            },
            "output_format": {"type": "string", "enum": ["png", "jpeg"], "default": "png"},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=100, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "model", "image_size"]
    side_effects = ["writes image file to output_path", "calls the KIE.ai API (costs credits)"]
    user_visible_verification = ["Inspect the generated image for relevance and quality"]

    def get_status(self) -> ToolStatus:
        if os.environ.get("KIE_API_KEY"):
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        # KIE bills in credits; these are the observed per-image list prices.
        return 0.04 if inputs.get("model", "nano-banana") == "nano-banana" else 0.02

    # ---- HTTP helpers ------------------------------------------------------

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        key = os.environ["KIE_API_KEY"]
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            f"{BASE_URL}{path}",
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read())
        if body.get("code") != 200:
            raise RuntimeError(f"KIE API error {body.get('code')}: {body.get('msg')}")
        return body.get("data") or {}

    def _submit(self, inputs: dict[str, Any]) -> tuple[str, str]:
        """Create a task. Returns (task_id, which_api)."""
        prompt = inputs["prompt"]
        size = inputs.get("image_size", "9:16")
        fmt = inputs.get("output_format", "png")

        if inputs.get("model", "nano-banana") == "gpt-image-1":
            data = self._request(
                "POST", "/api/v1/gpt4o-image/generate", {"prompt": prompt, "size": size}
            )
            return data["taskId"], "gpt4o"

        data = self._request(
            "POST",
            "/api/v1/jobs/createTask",
            {
                "model": "google/nano-banana",
                "input": {"prompt": prompt, "image_size": size, "output_format": fmt},
            },
        )
        return data["taskId"], "jobs"

    def _poll(self, task_id: str, which: str) -> list[str]:
        """Block until the task terminates. Returns the result image URLs."""
        path = (
            f"/api/v1/jobs/recordInfo?taskId={task_id}"
            if which == "jobs"
            else f"/api/v1/gpt4o-image/record-info?taskId={task_id}"
        )
        deadline = time.time() + POLL_TIMEOUT_SECONDS
        while time.time() < deadline:
            data = self._request("GET", path)
            state = str(data.get("state") or data.get("status") or "")
            if state in TERMINAL_FAILURE:
                raise RuntimeError(data.get("failMsg") or f"KIE task failed ({state})")
            if state in TERMINAL_SUCCESS:
                return _result_urls(data)
            time.sleep(POLL_INTERVAL_SECONDS)
        raise TimeoutError(f"KIE task {task_id} did not finish within {POLL_TIMEOUT_SECONDS}s")

    # ---- execute -----------------------------------------------------------

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if not os.environ.get("KIE_API_KEY"):
            return ToolResult(success=False, error="KIE_API_KEY not set. " + self.install_instructions)

        start = time.time()
        model = inputs.get("model", "nano-banana")
        try:
            task_id, which = self._submit(inputs)
            urls = self._poll(task_id, which)
            if not urls:
                return ToolResult(success=False, error="KIE returned no image URL")

            ext = inputs.get("output_format", "png")
            output_path = Path(inputs.get("output_path", f"kie_image.{ext}"))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(urls[0], timeout=120) as resp:
                output_path.write_bytes(resp.read())
        except Exception as exc:  # noqa: BLE001 — surface any provider failure to the agent
            return ToolResult(success=False, error=f"KIE image generation failed: {exc}")

        return ToolResult(
            success=True,
            data={
                "provider": "kie",
                "model": model,
                "prompt": inputs["prompt"],
                "output": str(output_path),
                "source_url": urls[0],
            },
            artifacts=[str(output_path)],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            model=model,
        )


def _result_urls(data: dict) -> list[str]:
    """Dig the image URLs out of whichever envelope this KIE API used."""
    raw = data.get("resultJson") or data.get("response") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    urls = raw.get("resultUrls") or raw.get("result_urls") or []
    return [u for u in urls if isinstance(u, str)]
