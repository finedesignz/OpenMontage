# OpenMontage

**Code:** OM

## What This Is

OpenMontage is an open-source, AI-orchestrated video production platform. The AI agent
is the intelligence; Python exists only for tools and persistence. Orchestration,
creative decisions, review, and stage transitions live in instructions — YAML pipeline
manifests plus markdown director/meta skills the agent follows.

State machine: `idea -> script -> scene_plan -> assets -> edit -> compose -> publish`.

## Core Value

Turn a brief or an existing deliverable into a finished, human-quality video through an
instruction-driven pipeline — no bespoke Python orchestrator, every creative and QC
decision made by the agent against declarative manifests, style playbooks, and schemas.

## Architecture (validated, already shipped)

- **Instruction-driven stages** — each stage has a director skill (MD); pipelines are
  declarative YAML in `pipeline_defs/` (`screen-demo`, `animated-explainer`,
  `talking-head`, `avatar-spokesperson`, `cinematic`, ... 13 total).
- **3 knowledge layers** — `tools/tool_registry.py` (what exists) → `skills/` (how OM
  uses them) → `.agents/skills/` (how the tech works). `agent_skills[]` bridges them.
- **Capability-first tools** — selector + provider pattern. TTS: `tts_selector` +
  `elevenlabs_tts` / `google_tts` / `openai_tts` / `piper_tts`. Video: `video_selector`
  + heygen/wan/hunyuan/ltx-local/ltx-modal/cogvideo/kling/runway/veo/seedance/...
- **Style playbooks** — `styles/*.yaml` (schema `schemas/styles/playbook.schema.json`):
  visual language, typography, motion, audio, asset constraints.
- **Canonical artifacts** — `brief`, `script`, `scene_plan`, `asset_manifest`,
  `edit_decisions`, `render_report`, `publish_log`, validated against
  `schemas/artifacts/*.schema.json`.
- **Meta skills** — `skills/meta/reviewer.md` (advisory, max 2 rounds),
  `checkpoint-protocol.md`, `skill-creator.md`. Cost tracker `tools/cost_tracker.py`.
- **hyperframes engine vendored** — `.agents/skills/hyperframes/*` (motion-principles,
  transitions, palettes, captions), `skills/hyperframes*`, `tools/video/hyperframes_compose.py`.
- **Render runtimes** — Remotion composer (`remotion-composer/`) + ffmpeg tool family.
- **API** — FastAPI (`api/`, `Dockerfile.api`), machine-key + Titanium magic-link +
  agent subscription-token auth. `openmontage` MCP server exposes jobs/pipelines.

## Validated Capabilities

- Screen-demo pipeline in `real_capture` mode: Playwright capture → Remotion overlay
  pass (cursor track, click ripples, ink callouts, zoom regions).
- `client-doc-walkthrough-video` skill (narrated screen walkthroughs of client HTML).
- ElevenLabs voice cloning with accent-safe spliced-pause prosody workflow.
- Piper local TTS (`en_US-lessac-medium.onnx` at repo root) as a free offline provider.

## Key Decisions

- **Instruction-driven, not Python-orchestrated** — the agent drives; Python is tools only.
- **Subscription-only agent auth** — never fall back to `ANTHROPIC_API_KEY`.
- **Dead credentials** — OpenAI key (401) and Google TTS billing are dead; ElevenLabs live.

## Current Milestone: v1.0 HF-PORT — Hyperframes Creative-Doctrine + Local-TTS + Storyboard

**Goal:** Absorb the transferable creative doctrine and per-project conventions that sit
*above* the already-vendored hyperframes engine, and add a first-class free local-TTS
provider — raising output quality and removing paid/dead-key dependency.

**Target features:**
- Motion-doctrine layer ("11 Laws") as an OM meta skill + style-playbook guidance.
- Kokoro-82M local TTS provider under `tts_selector` (upgrade path beyond Piper).
- Per-project `STORYBOARD.md` + `meta.json` convention with a beat-timeline approval
  gate and per-timestamp SFX / music-duck cues.
- Brand-lock DESIGN contract + style-philosophy overrides (brand-locked palette,
  varied motion vocabulary) for agency/client work.
- Raw-edit review-gate flow (trim-filler → approve-cut-list → animate) with named gates.

**Explicitly NOT adopting:** monolithic always-loaded docs (keep OM progressive
disclosure), Student-Edition teaching scaffolding, baked-in crypto/AIS domain examples.

**Source analysis:** `scratchpad/hyperframes-review.md` (comparative review).

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-20 — Milestone v1.0 HF-PORT started (GSD baseline bootstrapped for pre-existing project).*
