# Phase 1: Local TTS (Kokoro) - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Add Kokoro-82M as a first-class **free, offline TTS provider** to OpenMontage, slotting
into the existing capability-first `tts_selector` pattern, and define the selector's
fallback precedence so any pipeline can produce narration with zero paid/dead-key
dependency. Delivers requirements TTS-01, TTS-02, TTS-03.

**In scope:** a `kokoro_tts` BaseTool provider; its `.agents/skills` engine reference +
`agent_skills[]` bridge; documented selector fallback precedence.
**Out of scope:** voice cloning (Kokoro is synthesis-only — deferred), changes to
ElevenLabs/Piper providers, any pipeline-manifest rewrite (selector auto-discovers).
</domain>

<decisions>
## Implementation Decisions

### Provider integration (TTS-01, TTS-02)
- **D-01:** Implement `tools/audio/kokoro_tts.py` as a `BaseTool` mirroring
  `piper_tts.py` exactly — `capability="tts"`, `provider="kokoro"`, `tier=VOICE`,
  `runtime=ToolRuntime.LOCAL`, `determinism=DETERMINISTIC`, `execution_mode=SYNC`.
  The `tts_selector` auto-discovers any `capability="tts"` BaseTool from the registry,
  so **no selector edit is required** for discovery (only for precedence — see D-05).
  — **Reversibility:** reversible (new isolated file).
- **D-02:** `supports = {voice_cloning: False, multilingual: True, offline: True,
  native_audio: True}` and `best_for` reflecting Kokoro's edge over Piper: 54 voices,
  8 languages, higher expressive quality while still free/offline.
- **D-03:** Kokoro runs via the `kokoro`/`kokoro-onnx` Python package (ONNX runtime,
  CPU-capable), NOT a `cmd:` binary like Piper. `dependencies` declares the pip package;
  `install_instructions` gives the pip install + model/voices download. Model + voices
  cache under a stable dir (mirror Piper's `~/.piper` → `~/.kokoro` or repo-root cache);
  the exact package/model id is a RESEARCH item for the planner to pin.
- **D-04:** `input_schema` mirrors Piper's shape (`text`, `voice`/`speaker`, `speed`/
  `length_scale` analog, `output_path`) so the selector's pass-through call site needs
  no special-casing. `agent_skills = ["text-to-speech"]` at minimum; add a Kokoro engine
  reference under `.agents/skills/` (or reuse an existing generic TTS engine skill) to
  satisfy the Layer-1→Layer-3 bridge (TTS-02). Research: does an engine skill already
  exist, or must one be authored.

### Fallback precedence (TTS-03)
- **D-05:** Define the selector's provider ordering when `preferred_provider="auto"`:
  ElevenLabs (if key present + a specific voice/clone requested) → **Kokoro** (free,
  offline, multilingual, higher quality) → **Piper** (free, offline, last-resort). A run
  that explicitly requested a specific paid voice/clone must NOT silently downgrade to a
  free provider — it surfaces that the requested voice is unavailable (matches the
  existing accent-safe-voice contract). Free-tier auto runs pick Kokoro over Piper.
  — **Reversibility:** costly (touches selector scoring + is a documented contract).
- **D-06:** Document the precedence in the selector docstring/tool metadata AND in
  `PROJECT_CONTEXT.md`'s TTS bullet so future pipelines and agents rely on a stated
  contract, not implicit behavior.

### Claude's Discretion
- Exact Kokoro package (`kokoro` vs `kokoro-onnx`), pinned model id, and default voice —
  planner/researcher decide from current upstream (verify offline CPU path works on this
  Windows host; GPU optional).
- Whether the engine skill is new or an existing `text-to-speech` skill suffices.

## Deferred Ideas
- Kokoro voice-cloning parity with ElevenLabs — Kokoro is synthesis-only; its own phase.
</decisions>

## Downstream Notes
- Verification target: `tts_selector` with `preferred_provider="kokoro"` (or auto on a
  free-only env) synthesizes a WAV offline with no network + no paid key, and the
  registry lists `kokoro_tts` as an available `capability="tts"` provider.
