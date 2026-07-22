"""Tracer tests for the Kokoro (kokoro-onnx) offline TTS provider.

Proves the thinnest end-to-end slice of Phase HF-01:
  * offline synthesis produces a valid 24000 Hz non-silent WAV (TTS-01),
  * the provider is auto-discovered as a capability="tts" tool (D-01),
  * it is reachable through the TTSSelector contract (preferred_provider="kokoro"),
  * get_status() gates on BOTH import AND model files (RESEARCH pitfall 4).

Synthesis tests skip cleanly on hosts where the model files are not present,
so the suite stays green without the one-time ~340 MB download.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tools.audio.kokoro_tts import KokoroTTS
from tools.base_tool import (
    Determinism,
    ExecutionMode,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


def _model_dir() -> Path:
    return Path(os.environ.get("KOKORO_MODEL_DIR", Path.home() / ".kokoro"))


def _models_present() -> bool:
    d = _model_dir()
    return (d / "kokoro-v1.0.onnx").is_file() and (d / "voices-v1.0.bin").is_file()


def _kokoro_importable() -> bool:
    try:
        import kokoro_onnx  # noqa: F401
    except ImportError:
        return False
    return True


requires_engine = pytest.mark.skipif(
    not (_kokoro_importable() and _models_present()),
    reason="kokoro-onnx and/or model files not present (one-time download required)",
)


# ------------------------------------------------------------------
# Tool contract / identity
# ------------------------------------------------------------------


def test_kokoro_tool_identity():
    t = KokoroTTS()
    assert t.name == "kokoro_tts"
    assert t.capability == "tts"
    assert t.provider == "kokoro"
    assert t.tier == ToolTier.VOICE
    assert t.runtime == ToolRuntime.LOCAL
    assert t.determinism == Determinism.DETERMINISTIC
    assert t.execution_mode == ExecutionMode.SYNC
    assert t.stability == ToolStability.EXPERIMENTAL
    assert t.dependencies == ["python:kokoro_onnx"]
    # quality_score is the free-path precedence lever (D-05, TTS-03).
    assert t.quality_score == 0.7
    assert t.supports.get("multilingual") is True
    assert t.supports.get("offline") is True
    assert t.estimate_cost({"text": "hi"}) == 0.0
    assert "kokoro" in t.agent_skills


# ------------------------------------------------------------------
# Test 4 — get_status gating (import AND model files)
# ------------------------------------------------------------------


def test_get_status_unavailable_when_models_missing(tmp_path, monkeypatch):
    """kokoro_onnx importable but empty model dir -> UNAVAILABLE (pitfall 4)."""
    if not _kokoro_importable():
        pytest.skip("kokoro_onnx not installed")
    empty = tmp_path / "empty_models"
    empty.mkdir()
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(empty))
    assert KokoroTTS().get_status() == ToolStatus.UNAVAILABLE


@requires_engine
def test_get_status_available_when_models_present(monkeypatch):
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(_model_dir()))
    assert KokoroTTS().get_status() == ToolStatus.AVAILABLE


# ------------------------------------------------------------------
# Test 2 — auto-discovery (no selector edit)
# ------------------------------------------------------------------


def test_kokoro_auto_discovered_as_tts_provider():
    from tools.tool_registry import registry

    registry.ensure_discovered()
    names = [t.name for t in registry.get_by_capability("tts")]
    assert "kokoro_tts" in names


# ------------------------------------------------------------------
# Test 1 — offline synthesis (English happy path)
# ------------------------------------------------------------------


@requires_engine
def test_offline_synthesis_produces_non_silent_24k_wav(tmp_path, monkeypatch):
    import soundfile as sf

    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(_model_dir()))

    out = tmp_path / "kokoro_offline.wav"
    result = KokoroTTS().execute({"text": "Offline Kokoro test.", "output_path": str(out)})

    assert result.success, result.error
    assert out.is_file()
    samples, sr = sf.read(str(out))
    assert sr == 24000
    assert len(samples) > 0
    assert max(abs(samples.min()), abs(samples.max())) > 0.01  # non-silent


@requires_engine
def test_voice_id_passthrough_is_accepted(tmp_path, monkeypatch):
    """The selector passes a generic voice_id; execute() must accept it (A3)."""
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(_model_dir()))

    out = tmp_path / "kokoro_voiceid.wav"
    result = KokoroTTS().execute(
        {"text": "Voice id passthrough.", "voice_id": "af_heart", "output_path": str(out)}
    )
    assert result.success, result.error
    assert result.data.get("voice") == "af_heart"


# ------------------------------------------------------------------
# Test 3 — through the TTSSelector contract
# ------------------------------------------------------------------


@requires_engine
def test_selector_routes_to_kokoro_offline(tmp_path, monkeypatch):
    from tools.audio.tts_selector import TTSSelector

    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(_model_dir()))

    out = tmp_path / "kokoro_via_selector.wav"
    result = TTSSelector().execute(
        {
            "text": "Free offline narration through the selector.",
            "preferred_provider": "kokoro",
            "output_path": str(out),
        }
    )
    assert result.success, result.error
    assert result.data.get("selected_provider") == "kokoro"
    assert out.is_file()
