# Roadmap: OpenMontage — v1.0 HF-PORT

## Overview

Absorb the transferable hyperframes creative doctrine and per-project conventions that
sit *above* the already-vendored hyperframes engine, and add a first-class free local-TTS
provider. Work flows from the most self-contained, immediately-shippable capability (a
zero-cost Kokoro TTS provider that unblocks free narration) through the layered creative
conventions (motion doctrine → storyboard approval gate → brand-lock → raw-edit review
gates) that build on each other. Every phase delivers through an existing OpenMontage
construct — a `tts_selector` provider, a meta skill, an artifact + JSON schema, a style
playbook, or a checkpoint-protocol gate — so nothing reinvents the instruction-driven
platform.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Local TTS (Kokoro)** - Free offline `kokoro_tts` provider under `tts_selector` with documented fallback precedence
- [ ] **Phase 2: Motion Doctrine** - "11 Laws" meta skill wired into stage directors / playbook for motion-led pipelines
- [ ] **Phase 3: Storyboard Convention** - Per-project `STORYBOARD.md` + `meta.json` with a beat-timeline approval gate
- [ ] **Phase 4: Brand Lock** - Brand-locked DESIGN contract + style-philosophy override layered on style playbooks
- [ ] **Phase 5: Raw-Edit Review Gates** - Named trim-filler → cut-list → animate gates enforced via checkpoint-protocol

## Phase Details

### Phase 1: Local TTS (Kokoro)
**Goal**: A pipeline can produce narration with zero paid/dead-key dependency using a free, offline Kokoro-82M voice.
**Depends on**: Nothing (first phase — self-contained, unblocks free renders)
**Requirements**: TTS-01, TTS-02, TTS-03
**Success Criteria** (what must be TRUE):
  1. `kokoro_tts` exists as a `BaseTool`/ToolContract provider (mirroring `piper_tts`) and synthesizes a WAV from text offline
  2. `tts_selector` lists `kokoro_tts` with cost=0 / offline status and an `agent_skills[]` bridge to a `.agents/skills` engine reference
  3. When ElevenLabs is unavailable the selector falls back to Kokoro/Piper and produces narration with no paid/dead-key call
  4. A run that requested a specific ElevenLabs voice does NOT silently degrade — the documented precedence surfaces the substitution
**Plans**: 3 plans
- [ ] 01-01-PLAN.md — Tracer: kokoro_tts provider + one-time deps/model download + offline synthesis smoke (Wave 1)
- [ ] 01-02-PLAN.md — Selector no-silent-downgrade fix + documented ElevenLabs→Kokoro→Piper precedence (Wave 2)
- [ ] 01-03-PLAN.md — Multilingual 54-voice/8-language breadth + `.agents/skills/kokoro` engine bridge (Wave 2)

### Phase 2: Motion Doctrine
**Goal**: The agent consults hyperframes' motion "11 Laws" during scene_plan / edit for motion-led pipelines.
**Depends on**: Phase 1
**Requirements**: DOCTRINE-01, DOCTRINE-02
**Success Criteria** (what must be TRUE):
  1. An OM meta skill captures the OM-genericized "11 Laws" (one-idea-per-beat, black-is-canvas, symbolic palette, hold-the-hero-shot, the GSAP no-op anchor anti-bug, etc.)
  2. The doctrine skill is authored for progressive disclosure — referenced, not always-loaded monolithic
  3. The relevant stage director skills and/or playbook schema reference the doctrine so the agent applies it during scene_plan / edit for animated-explainer and the screen-demo overlay pass
**Plans**: TBD

### Phase 3: Storyboard Convention
**Goal**: A human approves a per-project beat timeline BEFORE any asset generation or render spend.
**Depends on**: Phase 2
**Requirements**: STORY-01, STORY-02, STORY-03
**Success Criteria** (what must be TRUE):
  1. A `STORYBOARD.md` artifact (beat timeline: per-beat duration, per-timestamp SFX cues, music-duck points) is defined with a JSON schema under `schemas/artifacts/`
  2. A per-project `meta.json` convention captures project-level audio/render settings aligned with the existing `projects/<name>/` layout
  3. The screen-demo (and animated-explainer) checkpoint-protocol includes a beat-timeline approval gate that blocks asset generation until the human approves
**Plans**: TBD

### Phase 4: Brand Lock
**Goal**: Agency/client work runs against a brand-locked palette while the look/motion vocabulary stays swappable.
**Depends on**: Phase 3
**Requirements**: BRAND-01, BRAND-02
**Success Criteria** (what must be TRUE):
  1. A brand-lock DESIGN contract (brand-derived locked palette + explicitly varied motion vocabulary) is expressible as/within a style playbook
  2. A style-philosophy override mechanism layers on `styles/*.yaml` so the look can change while the locked brand persists
  3. Loading a brand-locked playbook with a philosophy override yields the override look but preserves the locked palette (validated)
**Plans**: TBD

### Phase 5: Raw-Edit Review Gates
**Goal**: Raw footage moves through named review gates (trim-filler → approve-cut-list → animate) with enforced human approval.
**Depends on**: Phase 4
**Requirements**: EDITGATE-01, EDITGATE-02
**Success Criteria** (what must be TRUE):
  1. A raw-edit review flow (trim-filler → approve-cut-list → animate) is expressed in a pipeline manifest's stage/approval structure with named gates
  2. `skills/meta/checkpoint-protocol.md` enforces human_approval at the cut-list gate rather than via ad-hoc prompts
  3. A run cannot proceed to animate until the cut-list gate is approved by the human
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Local TTS (Kokoro) | 0/3 | Not started | - |
| 2. Motion Doctrine | 0/TBD | Not started | - |
| 3. Storyboard Convention | 0/TBD | Not started | - |
| 4. Brand Lock | 0/TBD | Not started | - |
| 5. Raw-Edit Review Gates | 0/TBD | Not started | - |
