# Milestones

## v1.0 HF-PORT (Shipped: 2026-07-24)

Ported hyperframes' creative doctrine + per-project conventions + a free local-TTS
provider into OpenMontage. See `scratchpad/hyperframes-review.md` for the source analysis.

**Phases completed:** 5 phases, 7 plans, 10 tasks

**Key accomplishments:**

- Free, offline Kokoro-82M neural TTS wired end-to-end as a `kokoro_tts` BaseTool — direct `execute()` and through the auto-discovering `tts_selector` both write a non-silent 24000 Hz WAV with zero paid/dead-key dependency and no network at inference.
- Closed the real silent-downgrade gap in `TTSSelector._select_best_tool` so an explicitly requested-but-unavailable provider (a requested paid voice) surfaces unavailability instead of quietly falling through to a free voice, and documented the ElevenLabs -> Kokoro -> Piper fallback precedence in both the selector docstring and PROJECT_CONTEXT.md. Free-path Kokoro>Piper ordering relies on the already-set `quality_score` lever with no scoring-engine edit.
- The proven English Kokoro tracer grown into the full 54-voice / 8-language offline provider by auto-deriving the espeak `lang` from each voice's prefix (explicit `lang` still wins), plus a dedicated `.agents/skills/kokoro/SKILL.md` engine reference that makes the `agent_skills=["kokoro"]` Layer-1 -> Layer-3 bridge real.
- Genericized hyperframes "11 Laws" into a progressive-disclosure OpenMontage meta skill (`skills/meta/motion-doctrine.md`) and wired stage-scoped consult hooks into the explainer scene/edit directors, screen-demo edit director, and reviewer - single source of truth, ASCII-clean, zero domain-leak strings.
- Added a per-project `storyboard` artifact + `project_meta` schema (both draft-2020-12, validated examples) and a `STORYBOARD.template.md`, then wired a mandatory beat-timeline human-approval gate into the screen-demo + animated-explainer `scene_plan` stage (approve before asset/render spend), documented in `checkpoint-protocol.md`.
- Added a brand-lock DESIGN contract (optional, back-compatible `brand_lock` schema block) plus `apply_philosophy()` in `playbook_loader.py` - a style-philosophy overlay swaps the look (motion/composition/texture/pace) while the locked brand palette/type is preserved byte-identical and a locked-field override is rejected. Kept the shared playbook schema strict (reverted an over-broad loosening; anime-ghibli stays excluded per the existing QA convention).
- Named the raw-edit review gates (trim_filler -> approve_cut_list -> animate) as `sub_stages` on the talking-head + podcast-repurpose `edit` stage with a human-approval gate on the cut list, enforced via `checkpoint-protocol.md`. Modeled the real `production_modes` field + `documentary` category in the manifest schema so all 13 pipelines validate.

---

Pre-GSD history (the platform existed and shipped before GSD tracking was added).
Baseline captured 2026-07-20 so the hyperframes port can run as a tracked milestone.

## Shipped before GSD (baseline — v0.x)

- Instruction-driven pipeline engine (13 `pipeline_defs/` manifests, director + meta skills).
- Capability-first tool families: `tts_selector`, `video_selector`, and providers.
- Screen-demo `real_capture` pipeline + Remotion overlay pass.
- `client-doc-walkthrough-video` skill (narrated client-HTML walkthroughs).
- ElevenLabs voice cloning with accent-safe spliced-pause prosody.
- Piper local TTS provider.
- FastAPI service + `openmontage` MCP server; 3-credential auth.
- hyperframes engine vendored (`.agents/skills/hyperframes/`, `hyperframes_compose.py`).

## In progress

- **v1.0 HF-PORT** — Hyperframes creative-doctrine + Kokoro local TTS + per-project
  storyboard/brand-lock conventions + raw-edit review gates. See PROJECT.md.
