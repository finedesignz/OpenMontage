"""Kokoro (kokoro-onnx) local text-to-speech provider tool.

Free, offline neural TTS using the Kokoro-82M model via ONNX Runtime. No paid
key, no network at inference time (the model files are downloaded once by
tools/audio/kokoro_model_setup.py into ~/.kokoro; override with KOKORO_MODEL_DIR).

Mirrors piper_tts.py's BaseTool shape so the tts_selector's generic pass-through
call site needs no special-casing. The engine differs: Kokoro runs as an
importable Python package (``python:kokoro_onnx``), not a ``cmd:`` binary, and
``kokoro.create()`` returns a float32 sample array that we write to WAV with
soundfile (RESEARCH pitfall 2).
"""

from __future__ import annotations

import os
import time
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

# Model file names for the pinned model-files-v1.0 release (see kokoro_model_setup.py).
_ONNX_FILE = "kokoro-v1.0.onnx"
_VOICES_FILE = "voices-v1.0.bin"

# Module-level Kokoro engine singletons keyed by resolved model dir. The ONNX
# graph takes seconds to load; re-instantiating per call is wasteful
# (RESEARCH pitfall 3).
_ENGINE_CACHE: dict[str, Any] = {}


def _model_dir() -> Path:
    """Resolve the Kokoro model cache dir (KOKORO_MODEL_DIR or ~/.kokoro)."""
    env = os.environ.get("KOKORO_MODEL_DIR")
    if env:
        return Path(env)
    return Path.home() / ".kokoro"


def _get_engine(model_dir: Path) -> Any:
    """Return a cached Kokoro engine for model_dir, loading it once."""
    key = str(model_dir.resolve())
    engine = _ENGINE_CACHE.get(key)
    if engine is None:
        from kokoro_onnx import Kokoro

        engine = Kokoro(
            str(model_dir / _ONNX_FILE),
            str(model_dir / _VOICES_FILE),
        )
        _ENGINE_CACHE[key] = engine
    return engine


class KokoroTTS(BaseTool):
    name = "kokoro_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "kokoro"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL

    dependencies = ["python:kokoro_onnx"]
    install_instructions = (
        "Install Kokoro (offline neural TTS):\n"
        '  pip install "kokoro-onnx==0.5.0" soundfile\n'
        "Then download the model files once (into ~/.kokoro, override KOKORO_MODEL_DIR):\n"
        "  python -m tools.audio.kokoro_model_setup\n"
        "Model files (pinned model-files-v1.0 release):\n"
        "  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx\n"
        "  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin\n"
        "Do NOT install system espeak-ng - it ships via espeakng-loader."
    )
    agent_skills = ["kokoro", "text-to-speech"]

    capabilities = [
        "text_to_speech",
        "offline_generation",
        "multilingual_generation",
    ]
    supports = {
        "voice_cloning": False,
        "multilingual": True,
        "offline": True,
        "native_audio": True,
    }
    best_for = [
        "free offline multilingual narration",
        "expressive local-only voiceover",
        "54-voice / 8-language narration",
    ]
    not_good_for = [
        "voice clone matching",
        "real-time streaming synthesis",
    ]

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "voice": {"type": "string", "default": "af_heart"},
            "speed": {"type": "number", "default": 1.0},
            "lang": {"type": "string", "default": "en-us"},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=2, ram_mb=1024, vram_mb=0, disk_mb=400, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=1, retryable_errors=[])
    idempotency_key_fields = ["text", "voice", "speed", "lang"]
    side_effects = ["writes audio file to output_path"]
    user_visible_verification = ["Listen to generated audio for intelligibility"]

    # Free-path precedence lever consumed by lib/scoring.py: orders Kokoro over
    # Piper on the auto free path (D-05, TTS-03). No scoring-engine edit needed.
    quality_score = 0.7

    def get_status(self) -> ToolStatus:
        """AVAILABLE only when kokoro_onnx imports AND both model files exist."""
        try:
            import kokoro_onnx  # noqa: F401
        except ImportError:
            return ToolStatus.UNAVAILABLE
        d = _model_dir()
        if (d / _ONNX_FILE).is_file() and (d / _VOICES_FILE).is_file():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(
                success=False,
                error="Kokoro TTS not available. " + self.install_instructions,
            )

        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"Kokoro TTS generation failed: {exc}")

        result.duration_seconds = round(time.time() - start, 2)
        return result

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        import soundfile as sf

        text = inputs["text"]
        # Accept the selector's generic voice_id pass-through (A3).
        voice = inputs.get("voice") or inputs.get("voice_id") or "af_heart"
        speed = float(inputs.get("speed", 1.0))
        # Tracer keeps lang caller-supplied/default; voice-prefix derivation is plan 01-03.
        lang = inputs.get("lang", "en-us")

        output_path = Path(inputs.get("output_path", "tts_output.wav"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        engine = _get_engine(_model_dir())
        samples, sample_rate = engine.create(text, voice=voice, speed=speed, lang=lang)
        sf.write(str(output_path), samples, sample_rate)

        if not output_path.exists():
            return ToolResult(success=False, error=f"Kokoro output file missing: {output_path}")

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "voice": voice,
                "lang": lang,
                "speed": speed,
                "sample_rate": sample_rate,
                "text_length": len(text),
                "output": str(output_path),
                "format": "wav",
            },
            artifacts=[str(output_path)],
            model="kokoro-82m",
        )
