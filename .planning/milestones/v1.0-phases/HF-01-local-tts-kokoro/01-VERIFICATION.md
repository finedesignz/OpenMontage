---
phase: HF-01-local-tts-kokoro
verified: 2026-07-22T00:00:00Z
status: passed
score: 4/4 success criteria verified (TTS-01 PASS, TTS-02 PASS, TTS-03 PASS)
behavior_unverified: 0
overrides_applied: 0
re_verification: false
---

# Phase HF-01: Local TTS (Kokoro) Verification Report

**Phase Goal:** A pipeline can produce narration with zero paid/dead-key dependency using a free, offline Kokoro-82M voice.
**Verified:** 2026-07-22
**Status:** PASSED
**Verifier:** Claude (independent, goal-backward). Did not build the phase.

## Goal Achievement — Observable Truths (ROADMAP Success Criteria)

| # | Truth (SC) | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `kokoro_tts` is a BaseTool provider (mirrors piper) that synthesizes a WAV from text offline | VERIFIED | `KokoroTTS(BaseTool)` capability=`tts`, provider=`kokoro`, runtime=`ToolRuntime.LOCAL`, tier=VOICE, determinism=DETERMINISTIC, execution_mode=SYNC. `get_status()` returns AVAILABLE only when `kokoro_onnx` imports AND both `kokoro-v1.0.onnx` + `voices-v1.0.bin` exist under `~/.kokoro`. Live run (ELEVENLABS_API_KEY unset in proc) via selector produced a 24000 Hz WAV, 94720 samples, peak 0.53, **rms 0.0753 (non-silent)**. estimate_cost=0.0. |
| 2 | `tts_selector` lists `kokoro_tts` with cost=0/offline + `agent_skills[]` bridge to a `.agents/skills` engine ref | VERIFIED | Registry `get_by_capability('tts')` auto-discovers `kokoro_tts` (no selector edit). `agent_skills=['kokoro','text-to-speech']`. `.agents/skills/kokoro/SKILL.md` exists, ASCII-clean (0 non-ASCII bytes). `kokoro-onnx==0.5.0` + `soundfile>=0.12` pinned in `requirements.txt`. |
| 3 | When ElevenLabs unavailable, selector falls back to Kokoro/Piper, no paid/dead-key call | VERIFIED | With ElevenLabs forced UNAVAILABLE, `preferred_provider='auto'` selected **kokoro**, success=True. Free-path rank order = `[kokoro, piper, elevenlabs, ...]` — kokoro ahead of piper via `quality_score=0.7`. |
| 4 | A run requesting a specific ElevenLabs voice does NOT silently degrade — precedence surfaces the substitution | VERIFIED | With ElevenLabs UNAVAILABLE, `preferred_provider='elevenlabs'` returned **success=False**: "Requested TTS provider 'elevenlabs' is unavailable -- not downgrading to a free voice." Known-but-unavailable returns `(None,None)` → surfaced; unknown name falls through to auto. Documented in selector docstring + `PROJECT_CONTEXT.md` lines 50-51. |

**Score:** 4/4 truths verified (0 behavior-unverified).

## Requirements Coverage

| Req | Description | Status | Evidence |
|-----|-------------|--------|----------|
| TTS-01 | `kokoro_tts` BaseTool exposing Kokoro-82M offline synth (54 voices, 8 langs) | PASS | Provider verified above; live `get_voices()` == **54**; lang derivation from voice prefix (ff_→fr-fr, zf_→cmn, jm_→ja, af_→en-us) across 17 prefixes / 8 languages. |
| TTS-02 | Register in selector, cost=0/offline, `agent_skills[]` bridge to `.agents/skills` | PASS | Auto-discovery + agent_skills bridge + SKILL.md + pinned deps verified above. |
| TTS-03 | Define + document fallback precedence, zero paid/dead-key narration | PASS | No-silent-downgrade + kokoro>piper precedence + docstring/PROJECT_CONTEXT docs verified above. |

## Behavioral Spot-Checks

| Behavior | Method | Result | Status |
|----------|--------|--------|--------|
| Offline synth non-silent 24000 Hz WAV, no paid key | selector `preferred_provider='kokoro'`, ELEVENLABS_API_KEY unset in proc | 24000 Hz, rms 0.0753, success | PASS |
| No-silent-downgrade | ElevenLabs forced UNAVAILABLE, explicit request | success=False, surfaced message | PASS |
| Auto free-path fallback | ElevenLabs UNAVAILABLE, auto | selected kokoro, success | PASS |
| Free precedence kokoro>piper | `operation='rank'` | `[kokoro, piper, ...]` | PASS |
| Multilingual lang derivation | `_lang_for_voice` | fr-fr/cmn/ja/en-us correct | PASS |
| Live voice breadth | `Kokoro.get_voices()` | 54 | PASS |
| No network at synth | Source review — synth imports only `kokoro_onnx`+`soundfile`, loads local model files, ONNX CPU inference; `get_status` gates on local files; `network_required=False` | no net calls | PASS |

## Test Suite

`pytest tests/tools/test_kokoro_tts.py tests/tools/test_tts_selector_downgrade.py tests/contracts/test_phase3_contracts.py -q`
→ **78 passed in 26.00s** (0 failed).

## Anti-Patterns

None blocking. `kokoro_tts.py` / `tts_selector.py` are substantive, wired, and data flows through real ONNX inference. Empty-return patterns present are legitimate error paths, not stubs. Pyright "import could not be resolved" for kokoro_onnx/soundfile confirmed false positives (runtime imports succeed; soundfile 0.14.0, kokoro_onnx present).

## Notes (non-blocking, INFO)

- `REQUIREMENTS.md` traceability table still marks **TTS-01 / TTS-02 as Pending** and their checkboxes `[ ]`, while TTS-03 is Complete. The **code fully delivers all three** — this is a stale tracking-status inconsistency, not a goal gap. Recommend flipping TTS-01/TTS-02 to Complete/`[x]` at closeout.
- Audio *intelligibility* (does it sound right) is quality-of-voice, listed under the tool's own `user_visible_verification`. The goal ("zero paid-dependency narration") is proven programmatically (non-silent WAV). An optional listen to the generated WAV is recommended but does not block the phase goal.

## Ship Verdict

**PASS — ship.** All 4 ROADMAP success criteria and all 3 requirements (TTS-01/02/03) are verified against the actual codebase with behavioral evidence (live offline synthesis, forced-unavailable downgrade, rank ordering, 54-voice breadth) plus 78 passing tests. The phase goal is achieved.

---
_Verified: 2026-07-22 — gsd-verifier (independent)_
