# Phase 2: Motion Doctrine - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Capture hyperframes' motion "11 Laws" as an OpenMontage **meta skill** (a Layer-2 project
convention), genericized and progressive-disclosure, and wire it into the stage director
skills for OM's motion-led pipelines so the agent consults it during `scene_plan` and
`edit`. Delivers DOCTRINE-01 (author the skill) and DOCTRINE-02 (wire it in).

**In scope:** one new `skills/meta/motion-doctrine.md`; reference hooks added to the
relevant director skills; a pre-flight checklist the reviewer/checkpoint can apply.
**Out of scope:** any Python/tool change; a full transitions catalog port; the crypto/AIS
domain examples from the source; rewriting the composer runtime.
</domain>

<decisions>
## Implementation Decisions

### The doctrine skill (DOCTRINE-01)
- **D-01:** Author `skills/meta/motion-doctrine.md` following OM's existing meta-skill
  shape (peer of `reviewer.md`, `checkpoint-protocol.md`). Source of truth =
  `../hyperframes/MOTION_PHILOSOPHY.md`, but **genericized**: keep the 11 Laws, the
  "cut this in half?" test, the pre-flight checklist, the anti-patterns, and the
  easing/pacing dictionary; **strip** all crypto/Infinite/AIS-specific examples and any
  GSAP-only API assumptions that don't apply to OM's Remotion runtime.
- **D-02:** Progressive disclosure — the skill is a compact core (the 11 Laws + the
  pre-flight checklist + the TL;DR) with deeper reference (timeline recipes, easing
  dictionary) in clearly-sectioned lower parts, so a director skill can point at just
  the core. Do NOT make it an always-loaded monolith (explicit anti-goal from PROJECT.md).
- **D-03:** Translate the two runtime-coupled laws to OM terms:
  - **Law #11 ("timelines fill their slots")** → OM's Remotion `calculateMetadata` +1s
    tail / black-frame-flash gotcha already documented in project memory
    `remotion-render-gotchas.md`; state it as the OM equivalent, not the GSAP no-op anchor.
  - **Velocity-matched quadratic easing at beat seams** → OM's screen-demo eased scrolls /
    overlay cursor easing. Keep the easing-by-purpose table as engine-neutral guidance.

### Wiring (DOCTRINE-02)
- **D-04:** Add a reference to the doctrine from the director skills of the motion-led
  pipelines at the stages where it bites:
  - `skills/pipelines/animated-explainer/scene-director.md` and `edit-director.md`
    (scene_plan + edit) — primary target.
  - `skills/pipelines/screen-demo/` edit/overlay director — the walkthrough overlay pass
    (eased scroll, cursor, callouts) is motion and benefits from the pacing/easing laws.
  - Wiring = a short "consult `skills/meta/motion-doctrine.md`" hook + which laws apply at
    that stage, NOT a copy of the doctrine into each director (single source of truth).
- **D-05:** Surface the pre-flight checklist to the reviewer meta skill so
  `skills/meta/reviewer.md` can apply the motion pre-flight to motion-led pipelines
  (advisory, consistent with its existing max-2-round advisory contract).

### Claude's Discretion
- Exact wording/section order of the skill; which laws are tagged per stage.
- Whether screen-demo's director files are one file or several (planner reads the dir).

## Deferred Ideas
- Full transitions-catalog port beyond the engine skill already vendored — its own phase.
</decisions>

## Downstream Notes
- Verification: `skills/meta/motion-doctrine.md` exists, ASCII-clean, contains all 11 Laws
  + pre-flight checklist; the named director skills each contain a reference hook to it;
  no crypto/AIS strings leak in; the skill index (`skills/INDEX.md`) lists it if that's
  the convention.
