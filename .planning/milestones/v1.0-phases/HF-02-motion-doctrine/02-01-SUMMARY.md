---
phase: HF-02-motion-doctrine
plan: 02-01
subsystem: skills
tags: [motion-graphics, meta-skill, remotion, doctrine, progressive-disclosure, docs]

# Dependency graph
requires:
  - phase: HF-01
    provides: OpenMontage Layer-2 skills architecture, explainer/screen-demo director skills
provides:
  - skills/meta/motion-doctrine.md meta skill (11 Laws, cut-this-in-half test, pre-flight checklist, easing/pacing/transition reference)
  - Reference hooks wiring the doctrine into explainer scene/edit directors, screen-demo edit director, and reviewer
  - Motion Doctrine row in skills/INDEX.md Meta Skills table
affects: [animated-explainer, screen-demo, animation, motion-graphics, reviewer, scene_plan, edit]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Progressive-disclosure meta skill: compact core (laws + checklist) with deeper reference below"
    - "Single source of truth: directors reference the doctrine, never copy its body"

key-files:
  created:
    - skills/meta/motion-doctrine.md
  modified:
    - skills/pipelines/explainer/scene-director.md
    - skills/pipelines/explainer/edit-director.md
    - skills/pipelines/screen-demo/edit-director.md
    - skills/meta/reviewer.md
    - skills/INDEX.md

key-decisions:
  - "Genericized the 11 Laws: stripped all crypto/Infinite/stablecoin/AIS domain examples; illustrate with neutral product-demo and report-walkthrough examples"
  - "Law 11 translated from the GSAP no-op-anchor to OM's Remotion calculateMetadata +1s tail / black-frame gotcha"
  - "Velocity-matched easing kept engine-neutral and grounded in OM screen-demo eased scrolls + overlay cursor easing"
  - "Wired the real explainer/ directory (plan named a non-existent animated-explainer/ path)"

patterns-established:
  - "Doctrine body lives in exactly one file; every director adds only a stage-scoped consult hook naming the laws that bite"
  - "Reviewer applies the motion pre-flight as advisory findings under the existing max-2-round contract"

requirements-completed: [DOCTRINE-01, DOCTRINE-02]

coverage:
  - id: D1
    description: "motion-doctrine.md meta skill exists, ASCII-clean, all 11 Laws + pre-flight checklist, zero domain-leak strings"
    requirement: DOCTRINE-01
    verification:
      - kind: other
        ref: "grep -cE law headings = 11; grep -riE 'infinite|stablecoin|AIS|crypto' = 0; LC_ALL=C non-ASCII = 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "scene-director, edit-director, screen-demo edit-director, and reviewer each carry a resolvable reference hook to the doctrine; INDEX lists it; body in exactly one file"
    requirement: DOCTRINE-02
    verification:
      - kind: other
        ref: "grep -c motion-doctrine.md across 5 files = 1 each; grep -rl '11 Laws (memorize)' = single file"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-07-24
status: complete
---

# Phase HF-02 Plan 02-01: Motion Doctrine Meta Skill + Wiring Summary

**Genericized hyperframes "11 Laws" into a progressive-disclosure OpenMontage meta skill (`skills/meta/motion-doctrine.md`) and wired stage-scoped consult hooks into the explainer scene/edit directors, screen-demo edit director, and reviewer - single source of truth, ASCII-clean, zero domain-leak strings.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 2 (tracer + expansion)
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments
- Authored `skills/meta/motion-doctrine.md`: compact core (11 genericized Laws, the cut-this-in-half pre-ship test, the pre-flight checklist, one-line TL;DR) plus reference (engine-neutral easing-by-purpose + stagger dictionary, pacing discipline, transition/motion vocabulary, anti-patterns, neutral illustrations).
- Translated the two runtime-coupled laws to OM terms: Law 11 -> Remotion `calculateMetadata` +1s tail / black-frame-flash (trim with `ffmpeg -t`); velocity-matched easing -> screen-demo eased scrolls + overlay cursor easing.
- Wired stage-scoped consult hooks into 4 surfaces, each naming only the laws that bite there; surfaced the pre-flight to the reviewer as an advisory review under its max-2-round contract; added the INDEX Meta Skills row.
- Enforced single source of truth: the doctrine body ("The 11 Laws (memorize)") appears in exactly one file; directors reference, never copy.

## Task Commits

1. **Task 1 (tracer): author skill + wire scene-director + verify** - `ca92bec` (feat)
2. **Task 2 (expansion): wire remaining directors + reviewer + index** - `1630a3a` (feat)

## Files Created/Modified
- `skills/meta/motion-doctrine.md` - New meta skill; genericized 11 Laws, pre-flight, reference dictionaries.
- `skills/pipelines/explainer/scene-director.md` - Step 4d consult hook (laws 1/4/8/9).
- `skills/pipelines/explainer/edit-director.md` - Step 5b consult hook (laws 1/5/9) + run pre-flight on timeline.
- `skills/pipelines/screen-demo/edit-director.md` - Section 5b consult hook (velocity-match easing + pacing laws 1/4).
- `skills/meta/reviewer.md` - Motion Doctrine Pre-flight Review (advisory, max-2-round) per D-05.
- `skills/INDEX.md` - Motion Doctrine row in Meta Skills table.

## Decisions Made
See frontmatter `key-decisions`. Notably: Law 11 mapped to the Remotion +1s tail gotcha (per project memory `remotion-render-gotchas.md`), and neutral examples (product demo, report walkthrough) replace all domain-specific reference material.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Corrected director directory path**
- **Found during:** Task 1 (wiring the tracer director)
- **Issue:** The plan frontmatter and body reference `skills/pipelines/animated-explainer/scene-director.md` and `.../edit-director.md`, but that directory does not exist. The actual pipeline directory is `skills/pipelines/explainer/` (confirmed via glob and INDEX.md, which labels it the "Animated Explainer Pipeline (`pipelines/explainer/`)").
- **Fix:** Wired the real `skills/pipelines/explainer/scene-director.md` and `edit-director.md`. Same intended targets, correct path.
- **Files modified:** skills/pipelines/explainer/scene-director.md, skills/pipelines/explainer/edit-director.md
- **Verification:** Both files now contain a resolvable `skills/meta/motion-doctrine.md` reference; the target file exists.
- **Committed in:** ca92bec (Task 1), 1630a3a (Task 2)

---

**Total deviations:** 1 auto-fixed (1 blocking path correction)
**Impact on plan:** No scope change - the "animated-explainer" name was a plan typo for the `explainer` directory. All four intended director surfaces plus the reviewer were wired as specified.

## Issues Encountered
- INDEX.md carries pre-existing mojibake (em-dash/arrow bytes from an earlier commit) throughout. Out of scope for this plan; the added Motion Doctrine row is ASCII-clean and no existing lines were altered.

## Screen-demo overlay director selection
Listed `skills/pipelines/screen-demo/` (8 stage directors). The overlay/edit pass is governed by `edit-director.md` (trims, speeds, overlays, subtitles, transitions, crop/ramp notes) - that is the file wired, per D-04.

## Next Phase Readiness
- DOCTRINE-01 and DOCTRINE-02 delivered. The doctrine is discoverable via INDEX and consulted at scene_plan and edit stages for motion-led pipelines.
- Deferred (own phase, per CONTEXT): full transitions-catalog port beyond the engine skill already vendored.

## Self-Check: PASSED
- skills/meta/motion-doctrine.md - FOUND
- .planning/phases/HF-02-motion-doctrine/02-01-SUMMARY.md - FOUND
- Commit ca92bec - FOUND
- Commit 1630a3a - FOUND

---
*Phase: HF-02-motion-doctrine*
*Completed: 2026-07-24*
