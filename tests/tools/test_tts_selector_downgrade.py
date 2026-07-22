"""Regression tests for the TTSSelector no-silent-downgrade contract (D-05, TTS-03).

An explicitly requested-but-unavailable provider (a requested paid voice, e.g.
ElevenLabs with no key) must surface unavailability instead of quietly falling
through to a free provider. An UNKNOWN preferred name still auto-ranks to an
available free provider. An available explicit preference is honored.

Hermetic: candidate providers are stubbed via monkeypatch on
``TTSSelector._providers`` with controlled ``get_status``. No ElevenLabs key and
no Kokoro/Piper model files are required.
"""

from __future__ import annotations

from typing import Any

import pytest

from tools.audio.tts_selector import TTSSelector
from tools.base_tool import BaseTool, ToolResult, ToolStatus


class _FakeFree(BaseTool):
    """An always-available free provider that writes a marker WAV."""

    name = "free_fake_tts"
    provider = "freefake"
    capability = "tts"
    quality_score = 0.7

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        out = inputs.get("output_path")
        if out:
            with open(out, "wb") as fh:
                fh.write(b"RIFF....WAVEfake")
        return ToolResult(success=True, data={"output_path": out})


class _FakeEleven(BaseTool):
    """A registered-but-unavailable paid provider (stands in for ElevenLabs)."""

    name = "fake_eleven_tts"
    provider = "elevenlabs"
    capability = "tts"

    def get_status(self) -> ToolStatus:
        return ToolStatus.UNAVAILABLE

    def execute(self, inputs: dict[str, Any]) -> ToolResult:  # pragma: no cover
        raise AssertionError("unavailable provider must never be executed")


@pytest.fixture
def selector(monkeypatch):
    sel = TTSSelector()
    monkeypatch.setattr(
        TTSSelector, "_providers", lambda self: [_FakeEleven(), _FakeFree()]
    )
    return sel


def test_no_silent_downgrade_for_unavailable_paid_request(selector, tmp_path):
    """Requested elevenlabs, key absent -> success=False, no WAV, no downgrade."""
    out = tmp_path / "should_not_exist.wav"
    result = selector.execute(
        {
            "text": "narration",
            "preferred_provider": "elevenlabs",
            "output_path": str(out),
        }
    )
    assert result.success is False
    assert "elevenlabs" in result.error
    assert "not downgrading" in result.error.lower()
    assert not out.exists(), "no WAV must be written on a refused downgrade"
    assert not result.data.get("selected_provider")


def test_unknown_provider_name_still_auto_ranks(selector, tmp_path):
    """A bogus (unregistered) preferred name falls through to the free auto pick."""
    out = tmp_path / "auto.wav"
    result = selector.execute(
        {
            "text": "narration",
            "preferred_provider": "bogus",
            "output_path": str(out),
        }
    )
    assert result.success is True, result.error
    assert result.data.get("selected_provider") == "freefake"
    assert out.exists()


def test_available_explicit_preference_is_honored(selector, tmp_path):
    """An explicit, available free provider is selected exactly."""
    out = tmp_path / "explicit.wav"
    result = selector.execute(
        {
            "text": "narration",
            "preferred_provider": "freefake",
            "output_path": str(out),
        }
    )
    assert result.success is True, result.error
    assert result.data.get("selected_provider") == "freefake"
    assert out.exists()
