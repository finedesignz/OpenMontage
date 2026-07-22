# Requirements — Milestone v1.0 HF-PORT

Scope: absorb the hyperframes creative doctrine + per-project conventions that sit above
the already-vendored engine, and add a free local-TTS provider. Each requirement maps to
an existing OM construct (meta skill, `tts_selector` provider, artifact + schema, style
playbook, or checkpoint-protocol gate) so nothing reinvents the platform.

Source analysis: `scratchpad/hyperframes-review.md`.

## v1.0 Requirements

### Motion Doctrine (DOCTRINE)

- [ ] **DOCTRINE-01**: Author an OM meta skill capturing hyperframes' "11 Laws" of motion
  (one-idea-per-beat, black-is-canvas, symbolic palette, hold-the-hero-shot, the GSAP
  no-op anchor anti-bug, etc.), OM-genericized and written for progressive disclosure
  (NOT a monolithic always-loaded doc).

- [ ] **DOCTRINE-02**: Wire the doctrine into the relevant stage director skills and/or
  style-playbook schema so the agent consults it during scene_plan / edit for the
  motion-led pipelines (animated-explainer, screen-demo overlay pass).

### Local TTS (TTS)

- [ ] **TTS-01**: Add a `kokoro_tts` provider tool (BaseTool/ToolContract, mirroring
  `piper_tts`) exposing Kokoro-82M offline synthesis (54 voices, 8 languages).

- [ ] **TTS-02**: Register `kokoro_tts` in `tts_selector` with cost=0 / offline status and
  an `agent_skills[]` bridge to a `.agents/skills` reference for the engine.

- [x] **TTS-03**: Define and document the selector's fallback precedence so a pipeline
  produces narration with zero paid/dead-key dependency (Kokoro/Piper) when ElevenLabs
  is unavailable — without silently degrading a run that requested a specific voice.

### Storyboard Convention (STORY)

- [ ] **STORY-01**: Define a per-project `STORYBOARD.md` artifact (beat timeline with
  per-beat duration, per-timestamp SFX cues, and music-duck points) plus a JSON schema
  under `schemas/artifacts/`.

- [ ] **STORY-02**: Define a per-project `meta.json` convention capturing project-level
  audio/render settings, aligned with OM's existing `projects/<name>/` layout.

- [ ] **STORY-03**: Wire a beat-timeline approval gate into the screen-demo (and
  animated-explainer) checkpoint-protocol so the human approves the beat timeline BEFORE
  asset generation / render spend.

### Brand Lock (BRAND)

- [ ] **BRAND-01**: Add a brand-lock DESIGN contract — a brand-derived locked palette with
  an explicitly varied motion vocabulary — expressible as/within a style playbook.

- [ ] **BRAND-02**: Provide a style-philosophy override mechanism layered on the existing
  `styles/*.yaml` playbooks (swap the look, keep the locked brand).

### Raw-Edit Review Gates (EDITGATE)

- [ ] **EDITGATE-01**: Define a raw-edit review flow (trim-filler → approve-cut-list →
  animate) with named review gates, expressed in a pipeline manifest's stage/approval
  structure.

- [ ] **EDITGATE-02**: Enforce those gates through `skills/meta/checkpoint-protocol.md`
  (human_approval at the cut-list gate) rather than ad-hoc prompts.

## Future Requirements (deferred)

- Kokoro voice-cloning parity with ElevenLabs (Kokoro is synthesis-only today).
- Porting hyperframes' full transitions catalog beyond what the engine skill already ships.

## Out of Scope (explicit exclusions)

- **Monolithic always-loaded docs** — hyperframes' 39KB always-on docs conflict with OM's
  progressive-disclosure layering. Reason: token cost + architecture mismatch.

- **Student-Edition teaching scaffolding** — OM agents are not learners. Reason: no fit.
- **Baked-in crypto/AIS domain examples** — must be genericized before any reuse.
  Reason: OM is domain-agnostic; agency/client work is the target.

- **Replacing the vendored hyperframes engine** — the engine already crossed over; this
  milestone is doctrine + conventions + TTS only.

## Traceability

Phase dirs/labels are milestone-scoped: `HF-NN-slug` (e.g. `HF-01-local-tts`).

| Requirement | Phase | Status |
|-------------|-------|--------|
| DOCTRINE-01 | Phase 2 (HF-02) | Pending |
| DOCTRINE-02 | Phase 2 (HF-02) | Pending |
| TTS-01 | Phase 1 (HF-01) | Pending |
| TTS-02 | Phase 1 (HF-01) | Pending |
| TTS-03 | Phase 1 (HF-01) | Complete |
| STORY-01 | Phase 3 (HF-03) | Pending |
| STORY-02 | Phase 3 (HF-03) | Pending |
| STORY-03 | Phase 3 (HF-03) | Pending |
| BRAND-01 | Phase 4 (HF-04) | Pending |
| BRAND-02 | Phase 4 (HF-04) | Pending |
| EDITGATE-01 | Phase 5 (HF-05) | Pending |
| EDITGATE-02 | Phase 5 (HF-05) | Pending |

Coverage: 12/12 requirements mapped, no orphans.
