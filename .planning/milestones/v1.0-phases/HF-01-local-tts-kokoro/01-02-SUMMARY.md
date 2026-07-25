---
phase: HF-01-local-tts-kokoro
plan: 2
subsystem: audio
tags: [tts, tts-selector, no-silent-downgrade, precedence, kokoro, piper, elevenlabs, scoring]

# Dependency graph
requires:
  - "01-01: kokoro_tts provider with quality_score=0.7 free-path ordering lever"
provides:
  - "TTSSelector no-silent-downgrade contract: explicit known-but-unavailable provider returns success=False with a specific 'not downgrading' message, no WAV (D-05, TTS-03)"
  - "Documented ElevenLabs -> Kokoro -> Piper fallback precedence in the selector docstring AND PROJECT_CONTEXT.md TTS bullet (D-06)"
  - "Regression test guarding the fall-through (tests/tools/test_tts_selector_downgrade.py)"
affects: [HF-01 plan 01-03 (multilingual breadth + kokoro skill)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Selector no-silent-downgrade: an explicit KNOWN-but-unavailable preferred_provider returns (None, None) from _select_best_tool; execute() surfaces a provider-specific message. Only an UNKNOWN name falls through to auto ranking."
    - "Free-path ordering via a provider-set quality_score lever (no scoring-engine edit)."

key-files:
  created:
    - tests/tools/test_tts_selector_downgrade.py
  modified:
    - tools/audio/tts_selector.py
    - PROJECT_CONTEXT.md

key-decisions:
  - "A1 verified: no code caller signals a paid voice via voice_id-only; no accent-safe-voice call path exists in pipelines/lib/tools. Scoped the explicit signal to preferred_provider alone; voice_id stays a generic pass-through (kokoro/piper depend on it per 01-01 A3)."
  - "Did NOT edit lib/scoring.py: Kokoro>Piper free-path ordering comes from kokoro_tts.quality_score=0.7 (deterministic +0.06 output_quality edge over Piper's 0.40)."
  - "Distinguish explicit-unavailable from no-providers inside execute() by re-deriving the KNOWN provider set, keeping the two selection loops separate (RESEARCH pitfall 6)."

requirements-completed: [TTS-03]

coverage:
  - id: D-05a
    description: "explicit unavailable paid request (elevenlabs, no key) -> success=False, specific not-downgrading message, no WAV, no selected_provider"
    requirement: "TTS-03"
    verification:
      - kind: unit
        ref: "tests/tools/test_tts_selector_downgrade.py#test_no_silent_downgrade_for_unavailable_paid_request"
        status: pass
      - kind: integration
        ref: "real registry, ElevenLabsTTS.get_status forced UNAVAILABLE -> refused, no WAV, no paid call"
        status: pass
    human_judgment: false
  - id: D-05b
    description: "unknown preferred_provider name still auto-ranks to an available free provider"
    requirement: "TTS-03"
    verification:
      - kind: unit
        ref: "tests/tools/test_tts_selector_downgrade.py#test_unknown_provider_name_still_auto_ranks"
        status: pass
    human_judgment: false
  - id: D-05c
    description: "explicit available preference is honored exactly"
    requirement: "TTS-03"
    verification:
      - kind: unit
        ref: "tests/tools/test_tts_selector_downgrade.py#test_available_explicit_preference_is_honored"
        status: pass
    human_judgment: false
  - id: D-05d
    description: "operation='rank' on the free path orders kokoro ahead of piper via quality_score (no scoring edit)"
    requirement: "TTS-03"
    verification:
      - kind: other
        ref: "rank probe: rankings order = ['kokoro','piper','elevenlabs','doubao','google_tts','openai']"
        status: pass
    human_judgment: false
  - id: D-06
    description: "ElevenLabs -> Kokoro -> Piper precedence + no-downgrade rule documented in selector docstring AND PROJECT_CONTEXT.md"
    requirement: "TTS-03"
    verification:
      - kind: other
        ref: "docstring contains Kokoro+Piper precedence; PROJECT_CONTEXT.md TTS bullet updated"
        status: pass
    human_judgment: false

# Metrics
duration: ~20min
completed: 2026-07-22
status: complete
---

# Phase HF-01 Plan 02: TTS Selector No-Silent-Downgrade + Documented Precedence Summary

**Closed the real silent-downgrade gap in `TTSSelector._select_best_tool` so an explicitly requested-but-unavailable provider (a requested paid voice) surfaces unavailability instead of quietly falling through to a free voice, and documented the ElevenLabs -> Kokoro -> Piper fallback precedence in both the selector docstring and PROJECT_CONTEXT.md. Free-path Kokoro>Piper ordering relies on the already-set `quality_score` lever with no scoring-engine edit.**

## Performance
- **Duration:** ~20 min
- **Started / Completed:** 2026-07-22
- **Tasks:** 2 (Task 1 TDD)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- **Task 1 (D-05):** `_select_best_tool` now returns `(None, None)` when `preferred_provider` names a KNOWN provider that is UNAVAILABLE, instead of falling through to the free auto loop. Only an UNKNOWN name auto-ranks. `execute()` turns that into a provider-specific `success=False` message (`"Requested TTS provider 'elevenlabs' is unavailable -- not downgrading to a free voice..."`), distinct from the generic `"No TTS provider available."`. Guarded by a 3-case regression test.
- **Task 2 (D-06):** Extended the `TTSSelector` module docstring with the ElevenLabs -> Kokoro -> Piper precedence and the no-downgrade rule; extended the PROJECT_CONTEXT.md capability-first TTS bullet with the same precedence + the "zero paid/dead-key free-path narration" contract. ASCII punctuation only (T-HF01-07). No `lib/scoring.py` edit.

## A1 Call-site Finding (required by plan output)
Grepped `pipelines/`, `lib/`, `tools/` for any caller that invokes the TTS capability / `tts_selector` with a paid-shaped `voice_id` but WITHOUT `preferred_provider`. **No such caller exists**, and there is **no "accent-safe-voice" call path in code** (the `accent` matches were all in unrelated skill / visual-style docs). TTS is invoked at the agent/skill layer via the `tts_selector` stage role, not a Python caller hardcoding a paid `voice_id`. Therefore the explicit "requested paid voice" signal is `preferred_provider` alone; `voice_id` remains a generic pass-through (kokoro/piper read it per 01-01's A3 finding), and is NOT treated as an implicit ElevenLabs request. Recorded as an inline comment in `_select_best_tool`.

## Verification Evidence
- **Regression suite:** `python -m pytest tests/tools/test_tts_selector_downgrade.py -q` -> **3 passed** (no-downgrade, unknown-name-auto-ranks, explicit-available-honored).
- **No-downgrade DoD (real registry):** with `ElevenLabsTTS.get_status` forced UNAVAILABLE against the otherwise-real registry, `execute(preferred_provider='elevenlabs')` -> `success=False`, message names the provider and says "not downgrading", **no WAV written, no paid API call**.
- **Free-path ordering:** `operation='rank'` (ElevenLabs excluded) -> `['kokoro','piper',...]` — kokoro ahead of piper via `quality_score=0.7`.
- **Docs present:** selector docstring contains the Kokoro/Piper precedence; PROJECT_CONTEXT.md TTS bullet updated.
- **Full tools suite:** `tests/tools/` green; only failure across `tests/contracts/test_phase3_contracts.py` is a pre-existing stale catalog assertion (see Deferred Issues) unrelated to this plan.

## Task Commits
1. **Task 1 (RED): failing no-downgrade regression** - `873863c` (test)
2. **Task 1 (GREEN): no-silent-downgrade fix** - `69ccfe7` (fix)
3. **Task 2: document precedence + no-downgrade** - `8e3de38` (docs)

## Files Created/Modified
- `tools/audio/tts_selector.py` - `_select_best_tool` no-fall-through for known-but-unavailable explicit provider; `execute()` provider-specific unavailable message; module docstring precedence + no-downgrade contract.
- `tests/tools/test_tts_selector_downgrade.py` - 3 hermetic regression tests (stubbed `_providers`, no ElevenLabs key / model files required).
- `PROJECT_CONTEXT.md` - TTS bullet records the ElevenLabs -> Kokoro -> Piper precedence and the no-downgrade contract.

## Decisions Made
- Followed RESEARCH D-05/D-06 verbatim, including its exact fix shape and pitfall-6 guard (kept the two selection loops separate).
- Scoped the explicit signal to `preferred_provider` per the A1 verification (no `voice_id`-only heuristic added — it would have no caller and would break kokoro/piper `voice_id` pass-through).

## Deviations from Plan
None - plan executed exactly as written.

## Deferred Issues
- **`tests/contracts/test_phase3_contracts.py::TestCapabilityMetadata::test_registry_catalog_views`** fails (pre-existing): it hardcodes the TTS provider set as `{elevenlabs, google_tts, openai, piper}`, but the registry now also discovers `kokoro` (added by plan 01-01) and pre-existing `doubao`. Confirmed to fail with this plan's changes stashed, so it is not caused by the selector edit and is out of this plan's declared file scope. Logged to `deferred-items.md`; the stale set belongs to the kokoro/doubao provider additions (a phase-cleanup or 01-03 concern). Not touched to avoid colliding with parallel plan 01-03.

## Environment Note
`tools/base_tool.py` / `tools/tool_registry.py` auto-load `.env` (via `lib/env_loader`) on import and on every `registry.ensure_discovered()`, which repopulates the live `ELEVENLABS_API_KEY` present in this environment. That is why the no-downgrade DoD cannot be shown by merely `os.environ.pop`-ing the key against the real registry (the reload re-arms it and would make a real paid call); the plan's hermetic stub tests are the authoritative proof, and the DoD was additionally demonstrated by forcing only `ElevenLabsTTS.get_status` UNAVAILABLE.

## Self-Check: PASSED
- Created file present: `tests/tools/test_tts_selector_downgrade.py`, `01-02-SUMMARY.md`.
- Modified files present: `tools/audio/tts_selector.py`, `PROJECT_CONTEXT.md`.
- Task commits present: `873863c`, `69ccfe7`, `8e3de38`.

---
*Phase: HF-01-local-tts-kokoro*
*Completed: 2026-07-22*
