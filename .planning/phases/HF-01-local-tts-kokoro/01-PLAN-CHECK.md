# Plan Check — Phase HF-01 Local TTS (Kokoro)

**Verdict:** PASS
**Checked:** 2026-07-22
**Plans:** 01-01 (wave 1 tracer), 01-02 (wave 2), 01-03 (wave 2)

## Coverage
| Req | Plans | Status |
|-----|-------|--------|
| TTS-01 | 01-01, 01-03 | Covered (tracer English + 01-03 multilingual breadth) |
| TTS-02 | 01-01, 01-03 | Covered (agent_skills field + SKILL.md authored) |
| TTS-03 | 01-01, 01-02 | Covered (quality_score lever + downgrade fix + docs) |

All three req IDs present in plan frontmatter `requirements`. No orphan.

## Decisions D-01..D-06
D-01 mirror piper/runtime LOCAL (01-01 T2); D-02 supports.multilingual+best_for (01-01 T2, 01-03 T1); D-03 kokoro-onnx pkg + ~/.kokoro (01-01 T1); D-04 input_schema+agent_skills (01-01, 01-03); D-05 precedence+no-silent-downgrade (01-01 quality_score, 01-02 T1); D-06 docstring+PROJECT_CONTEXT (01-02 T2). All addressed, none reduced/deferred.

## Findings

1. Anchor verification (BLOCKER-class check → PASS). Opened tts_selector.py.
   `_select_best_tool` exists (L157). L178-181 = `if preferred != "auto":` loop; L183-185 = auto fall-through; L140-141 = execute() `if tool is None: return "No TTS provider available."`. The silent-downgrade bug is REAL: an explicit `preferred_provider` that is registered-but-UNAVAILABLE finds no match in the preferred loop and falls through to the auto loop. RESEARCH's fix and line cites are accurate, not hallucinated.

2. Tracer end-to-end (PASS). 01-01 spans deps+model-download → provider tool → registry auto-discovery → through-selector call producing a non-silent 24000Hz WAV. Both expansions depend_on 01-01, so the slice is proven before breadth.

3. Wave-2 parallelism safe (PASS). 01-02 files = {tts_selector.py, test_tts_selector_downgrade.py, PROJECT_CONTEXT.md}; 01-03 files = {kokoro_tts.py, test_kokoro_tts.py, .agents/skills/kokoro/SKILL.md}. Zero overlap. 01-03 touches kokoro_tts.py/test which 01-01 created, but 01-03 depends_on 01-01 (sequential) — safe.

4. Verify commands executable (PASS). ProviderScore.to_dict() = asdict() includes `provider` + `tool_name`, so 01-02's `x['provider']` rank assertion works. 01-01/01-03 pytest+discovery commands runnable. "Free" is proven (ELEVENLABS_API_KEY unset); "offline" is architecturally guaranteed (network_required=False, no API in synth path) + manual network-off note.

5. Assumptions A1/A2/A3 all verify-then-proceed, not silent. A3 in 01-01 T2 (grep callers for model/speaker_id-only), A1 in 01-02 T1 (trace accent-safe voice_id path FIRST), A2 in 01-03 T1 (enumerate installed voices FIRST). Each records finding in summary.

6. Scope sane: 2 tasks/plan, ≤4 files/plan. Well within budget.

## Warnings (non-blocking)
- W1: 01-01 automated verify does not programmatically disable network to hard-prove offline; relies on architectural guarantee + manual note. Acceptable (synth path has no network call), but a `network-disabled` CI harness would strengthen the DoD.
- W2: 01-02 A1 finding and 01-01 A3 finding are consumed by parallel wave-2 plans via 01-01 summary; ensure 01-01 summary is written before wave 2 dispatch (orchestrator already enforces via depends_on).

No blockers. Proceed to execute.
