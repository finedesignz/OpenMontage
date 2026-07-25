---
phase: HF-01-local-tts-kokoro
plan: 1
subsystem: audio
tags: [tts, kokoro, kokoro-onnx, onnxruntime, soundfile, offline, base-tool, tts-selector]

# Dependency graph
requires: []
provides:
  - "kokoro_tts BaseTool provider (capability=tts, provider=kokoro, runtime=LOCAL) — free offline neural TTS"
  - "kokoro_model_setup.py idempotent one-time model-file downloader into ~/.kokoro (KOKORO_MODEL_DIR override)"
  - "kokoro-onnx==0.5.0 + soundfile>=0.12 pinned in requirements.txt"
  - "quality_score=0.7 free-path precedence lever (scoring-engine consumes it, no scoring edit)"
  - "auto-discovery of kokoro_tts by registry + tts_selector, no selector edit (D-01)"
affects: [HF-01 plan 01-02 (selector precedence + ordering), HF-01 plan 01-03 (multilingual breadth + kokoro skill)]

# Tech tracking
tech-stack:
  added: [kokoro-onnx==0.5.0, soundfile>=0.12, onnxruntime (transitive), espeakng-loader (transitive), phonemizer-fork (transitive)]
  patterns:
    - "Offline neural TTS provider: python: import dependency + one-time model download, not a cmd: binary"
    - "Module-level engine singleton keyed by model dir to avoid per-call ONNX load"
    - "get_status() gates on BOTH import AND model-file presence"

key-files:
  created:
    - tools/audio/kokoro_tts.py
    - tools/audio/kokoro_model_setup.py
    - tests/tools/test_kokoro_tts.py
  modified:
    - requirements.txt

key-decisions:
  - "kokoro-onnx==0.5.0 (ONNX, no PyTorch) over official kokoro (PyTorch+misaki) — Windows-clean, espeak-ng bundled via espeakng-loader"
  - "Pinned model-files-v1.0 release URLs (no floating latest); HTTPS-only, idempotent skip-if-present (threat T-HF01-01)"
  - "execute() reads voice|voice_id|af_heart so the selector's generic voice_id passes through (A3)"
  - "lang kept caller-supplied/default (en-us) in the tracer; voice-prefix auto-derivation deferred to plan 01-03"

patterns-established:
  - "Free-path scoring lever: set quality_score on a provider class; lib/scoring.py uses it directly (0.7 > Piper's stability-derived 0.4)"
  - "Model singleton cache keyed by resolved model dir (RESEARCH pitfall 3)"

requirements-completed: [TTS-01, TTS-02, TTS-03]

coverage:
  - id: D1
    description: "kokoro_tts.execute() synthesizes a non-silent 24000 Hz WAV offline with no paid/dead key"
    requirement: "TTS-01"
    verification:
      - kind: unit
        ref: "tests/tools/test_kokoro_tts.py#test_offline_synthesis_produces_non_silent_24k_wav"
        status: pass
      - kind: other
        ref: "direct-engine probe: Kokoro.create('Offline Kokoro test.') -> sr=24000, samples=37376, peak=0.4851"
        status: pass
    human_judgment: false
  - id: D2
    description: "registry auto-discovers kokoro_tts as a capability=tts provider (no selector edit)"
    requirement: "TTS-02"
    verification:
      - kind: unit
        ref: "tests/tools/test_kokoro_tts.py#test_kokoro_auto_discovered_as_tts_provider"
        status: pass
      - kind: other
        ref: "registry.get_by_capability('tts') includes kokoro_tts -> 'discovery ok'"
        status: pass
    human_judgment: false
  - id: D3
    description: "TTSSelector(preferred_provider='kokoro') routes to kokoro and writes a WAV offline, ELEVENLABS_API_KEY unset"
    requirement: "TTS-03"
    verification:
      - kind: integration
        ref: "tests/tools/test_kokoro_tts.py#test_selector_routes_to_kokoro_offline"
        status: pass
    human_judgment: false
  - id: D4
    description: "get_status() gates on import AND model files (UNAVAILABLE when models absent)"
    requirement: "TTS-01"
    verification:
      - kind: unit
        ref: "tests/tools/test_kokoro_tts.py#test_get_status_unavailable_when_models_missing"
        status: pass
    human_judgment: false
  - id: D5
    description: "quality_score=0.7 set as the free-path ordering lever (ordering itself verified in plan 01-02)"
    requirement: "TTS-03"
    verification:
      - kind: unit
        ref: "tests/tools/test_kokoro_tts.py#test_kokoro_tool_identity"
        status: pass
    human_judgment: false

# Metrics
duration: ~15min
completed: 2026-07-22
status: complete
---

# Phase HF-01 Plan 01: Kokoro Offline TTS Tracer Summary

**Free, offline Kokoro-82M neural TTS wired end-to-end as a `kokoro_tts` BaseTool — direct `execute()` and through the auto-discovering `tts_selector` both write a non-silent 24000 Hz WAV with zero paid/dead-key dependency and no network at inference.**

## Performance

- **Duration:** ~15 min (excl. ~340 MB one-time model download)
- **Started:** 2026-07-22
- **Completed:** 2026-07-22
- **Tasks:** 2
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments
- Pinned `kokoro-onnx==0.5.0` + `soundfile>=0.12`; installed both plus transitive deps (onnxruntime, espeakng-loader, phonemizer-fork) — no system espeak-ng.
- `kokoro_model_setup.py` downloaded the two pinned model-files-v1.0 assets into `~/.kokoro` (`kokoro-v1.0.onnx` 325,532,387 bytes; `voices-v1.0.bin` 28,214,398 bytes); helper is idempotent (skip-if-present).
- `KokoroTTS(BaseTool)` provider mirroring `piper_tts.py`: offline synthesis, import+model-file gated `get_status()`, module-level engine singleton, `quality_score=0.7`, `estimate_cost=0.0`.
- Auto-discovered by the registry and reachable through `TTSSelector(preferred_provider="kokoro")` with **no selector edit** (D-01).
- 7 new tracer tests pass; full `tests/tools/` suite (84 tests) green — no regressions.

## Verification Evidence
- **Unit suite:** `python -m pytest tests/tools/test_kokoro_tts.py -x -q` → **7 passed in 7.65s**.
- **Direct-engine offline WAV probe (DoD):** `Kokoro.create("Offline Kokoro test.", voice="af_heart", speed=1.0, lang="en-us")` → **`DIRECT-ENGINE OK sr=24000 samples=37376 peak=0.4851`** (24000 Hz, ~1.56s, clearly non-silent).
- **Discovery:** `registry.get_by_capability('tts')` includes `kokoro_tts` → `discovery ok`.
- **Through-the-contract:** `TTSSelector.execute(preferred_provider='kokoro', ELEVENLABS_API_KEY unset)` → `success`, `selected_provider == 'kokoro'`, WAV written (test_selector_routes_to_kokoro_offline).
- **Gating:** with `KOKORO_MODEL_DIR` pointed at an empty dir, `get_status()` → `UNAVAILABLE` even though `kokoro_onnx` imports.
- **Regression:** `python -m pytest tests/tools/ -q` → **84 passed** in 77s.

## Task Commits

1. **Task 1: Pin deps + model-file downloader** - `48f0f73` (feat)
2. **Task 2 (RED): failing tracer tests** - `9ed9699` (test)
3. **Task 2 (GREEN): KokoroTTS provider** - `902a518` (feat)

_TDD task 2 = test → feat (no refactor commit needed)._

## Files Created/Modified
- `tools/audio/kokoro_tts.py` - KokoroTTS BaseTool provider (offline synthesis, get_status gating, singleton engine, quality_score lever).
- `tools/audio/kokoro_model_setup.py` - idempotent `ensure_models()` + `__main__` downloader for the two pinned model assets.
- `tests/tools/test_kokoro_tts.py` - 7 tracer tests (identity, gating, discovery, offline synth, voice_id passthrough, selector routing).
- `requirements.txt` - pinned kokoro-onnx==0.5.0 + soundfile>=0.12 under a "Local TTS (Kokoro)" comment.

## Decisions Made
- Followed the plan/RESEARCH field table verbatim. All four RESEARCH pitfalls avoided (no per-call re-instantiation, `soundfile.write` of float32 samples, import+file gating, no system espeak-ng).

## A3 Call-site Finding (recorded for plans 01-02 / 01-03)
Grepped `pipelines/`, `lib/`, `tools/` for TTS callers passing Piper's `model`/`speaker_id` keys without `voice`/`voice_id`. **No caller relies on `model`/`speaker_id`-only** — the only `speaker_id` references are inside `piper_tts.py` itself, and no pipeline invokes `tts_selector`/`TTSSelector` with those keys. The selector passes `voice_id`/`model_id` through; Kokoro's `execute()` reads `voice or voice_id or "af_heart"`, which fully covers the selector's generic `voice_id` pass-through. No extra fallback key was needed.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None. (Benign pip warnings about a pre-existing invalid `~angchain-core` distribution and off-PATH console scripts — unrelated to this plan, not fixed per scope boundary.)

## User Setup Required
None for inference. The one-time ~340 MB model download was performed during this plan and is cached in `~/.kokoro`; other machines run `python -m tools.audio.kokoro_model_setup` once (needs network for that single step only).

## Next Phase Readiness
- Proven offline slice ready for wave 2 expansion:
  - **Plan 01-02:** selector no-silent-downgrade fix (`_select_best_tool` L178-187) + Kokoro>Piper ordering assertion (quality_score lever already in place).
  - **Plan 01-03:** multilingual voice/lang breadth (voice-prefix → espeak lang derivation) + `.agents/skills/kokoro/SKILL.md` (agent_skills already references `"kokoro"`).
- No blockers.

## Self-Check: PASSED
- All created files present (kokoro_tts.py, kokoro_model_setup.py, test_kokoro_tts.py, 01-01-SUMMARY.md).
- All task commits present (48f0f73, 9ed9699, 902a518).
- requirements.txt pins kokoro-onnx==0.5.0.

---
*Phase: HF-01-local-tts-kokoro*
*Completed: 2026-07-22*
