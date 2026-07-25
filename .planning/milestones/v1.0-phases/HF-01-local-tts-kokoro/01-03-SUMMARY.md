---
phase: HF-01-local-tts-kokoro
plan: 3
subsystem: audio
tags: [tts, kokoro, kokoro-onnx, multilingual, espeak, agent-skills, offline]

# Dependency graph
requires:
  - "kokoro_tts BaseTool tracer (plan 01-01) — English happy-path execute() + singleton engine"
provides:
  - "Multilingual kokoro_tts: espeak lang auto-derived from voice prefix (17 prefixes -> 9 espeak strings -> 8 languages); explicit lang overrides"
  - ".agents/skills/kokoro/SKILL.md engine reference completing the agent_skills=['kokoro'] Layer-1 -> Layer-3 bridge"
  - "_PREFIX_LANG map + _lang_for_voice() helper (A2-verified against installed get_voices())"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Voice-prefix -> espeak lang derivation: caller omits lang, provider derives from the 2-char voice prefix; explicit lang always wins"

key-files:
  created:
    - .agents/skills/kokoro/SKILL.md
  modified:
    - tools/audio/kokoro_tts.py
    - tests/tools/test_kokoro_tts.py

key-decisions:
  - "Derive espeak lang from voice prefix only when no explicit lang is passed; explicit inputs['lang'] always overrides (D-02)"
  - "Removed the schema's fixed lang default (en-us) in favor of documented auto-derivation, so multilingual voices work without the caller knowing espeak strings"
  - "Authored a dedicated .agents/skills/kokoro/SKILL.md (the existing text-to-speech skill teaches HeyGen, not Kokoro) — keeps agent_skills=['kokoro','text-to-speech'] honest"

patterns-established:
  - "A2 verify-then-proceed: enumerate installed get_voices() + probe each espeak string via create() BEFORE trusting the RESEARCH map"

requirements-completed: [TTS-01, TTS-02]

# Metrics
duration: ~20min
completed: 2026-07-22
status: complete
---

# Phase HF-01 Plan 03: Kokoro Multilingual Breadth + Engine Skill Summary

**The proven English Kokoro tracer grown into the full 54-voice / 8-language offline provider by auto-deriving the espeak `lang` from each voice's prefix (explicit `lang` still wins), plus a dedicated `.agents/skills/kokoro/SKILL.md` engine reference that makes the `agent_skills=["kokoro"]` Layer-1 -> Layer-3 bridge real.**

## Performance
- **Duration:** ~20 min
- **Started/Completed:** 2026-07-22
- **Tasks:** 2 (Task 1 TDD)
- **Files modified:** 3 (1 created, 2 modified)

## A2 Inventory Finding (verify-then-proceed, done FIRST)
Enumerated the installed `kokoro-onnx` voices via `Kokoro.get_voices()` and probed every espeak string via `create()` BEFORE coding the map:
- **54 voices, 17 prefixes** — exactly matching RESEARCH: `af am bf bm ef em ff hf hm if im jf jm pf pm zf zm`.
- **All 9 espeak lang strings** (`en-us, en-gb, es, fr-fr, hi, it, ja, pt-br, cmn`) accepted by `create()` and produced non-silent output.
- **Result: ZERO drift** from the 01-RESEARCH.md prefix->lang table. Assumption A2 fully confirmed; the RESEARCH map was used verbatim. 17 prefixes -> 9 espeak strings -> 8 languages (American af/am + British bf/bm English are one language, two espeak strings).

## Accomplishments
- `_PREFIX_LANG` map + `_lang_for_voice()` helper (falls back to `en-us` for an unknown prefix).
- `execute()` now derives `lang` from the voice prefix when the caller passes none; an explicit `inputs["lang"]` always overrides. English happy path and voice/voice_id/af_heart resolution unchanged.
- `input_schema` `lang` property re-documented for auto-derivation (removed the misleading fixed `en-us` default).
- New tests: prefix-map coverage (off-host, no engine), 54/8 inventory (engine), multilingual auto-lang (ff_siwis -> fr-fr, non-silent), explicit-lang-override (bf_emma + en-us), voice_id lang-derivation (bf_emma -> en-gb).
- Authored `.agents/skills/kokoro/SKILL.md`: install, one-time model files, `create()` API, 24000 Hz, voice-prefix->lang map, `af_heart`, Apache-2.0. ASCII punctuation only.

## Verification Evidence
- `python -m pytest tests/tools/test_kokoro_tts.py -q` -> **12 passed in 8.33s** (5 new + 7 tracer).
- Multilingual: `ff_siwis` with NO lang -> `data.lang == "fr-fr"`, 24000 Hz, non-silent WAV.
- Override: `bf_emma` + explicit `lang="en-us"` -> `data.lang == "en-us"` (prefix would derive en-gb).
- voice_id path: `voice_id="bf_emma"` (no voice key) -> `data.voice == "bf_emma"`, `data.lang == "en-gb"`.
- Inventory (installed engine): `len(get_voices()) == 54`, derived langs == the 9-string / 8-language set.
- SKILL bridge: `name: kokoro` frontmatter + engine facts present; `'kokoro' in KokoroTTS.agent_skills` -> `bridge ok`. ASCII-clean (no em/en-dash, curly quotes, ellipsis).

## Task Commits
1. **Task 1 (RED): failing multilingual + inventory tests** - `9626ca0` (test)
2. **Task 1 (GREEN): voice-prefix lang derivation** - `fc3c0a7` (feat)
3. **Task 2: .agents/skills/kokoro/SKILL.md** - `45d2f68` (docs)

## Files Created/Modified
- `tools/audio/kokoro_tts.py` - `_PREFIX_LANG` map + `_lang_for_voice()`; `execute()` auto-derives lang; schema `lang` re-documented.
- `tests/tools/test_kokoro_tts.py` - 5 new tests (map coverage, inventory, multilingual auto-lang, explicit override, voice_id lang-derivation).
- `.agents/skills/kokoro/SKILL.md` - kokoro-onnx engine reference (Layer-3 bridge).

## Deviations from Plan
None - plan executed exactly as written. A2 confirmed with zero drift, so the RESEARCH map was used verbatim.

## Issues Encountered
- Full `tests/tools/` run shows **1 failure in `tests/tools/test_tts_selector_downgrade.py`** — this is **plan 01-02's file** (committed `873863c test(HF-01-02): add failing regression for TTS no-silent-downgrade`), an intentional TDD RED awaiting 01-02's selector GREEN fix. **Out of my scope** (Wave 2 parallel; I was instructed not to touch `tts_selector.py` / `test_tts_selector_downgrade.py`). Not a defect I own and independent of my changes — all 12 kokoro tests pass. No action taken.

## Known Stubs
None.

## User Setup Required
None. Model files already cached in `~/.kokoro` from plan 01-01.

## Self-Check: PASSED
- `.agents/skills/kokoro/SKILL.md` present; `tools/audio/kokoro_tts.py` + `tests/tools/test_kokoro_tts.py` modified.
- Commits present: 9626ca0 (test), fc3c0a7 (feat), 45d2f68 (docs).
- `KokoroTTS.agent_skills` includes 'kokoro'; 12/12 kokoro tests green.

---
*Phase: HF-01-local-tts-kokoro*
*Completed: 2026-07-22*
