---
phase: 5
plan: "05-01"
subsystem: pipelines
tags: [pipeline-manifest, checkpoint-protocol, review-gates, edit-decisions]
requires:
  - schemas/pipelines/pipeline_manifest.schema.json (sub_stages field, unchanged)
  - lib/pipeline_loader.py (load_pipeline, get_stage_sub_stages)
provides:
  - talking-head edit stage named gates (trim_filler -> approve_cut_list -> animate)
  - podcast-repurpose edit stage named gates (same sequence)
  - checkpoint-protocol Raw-Edit Cut-List Gate section
affects:
  - raw-footage edit flow (human sign-off on cut list before render spend)
tech-stack:
  added: []
  patterns:
    - Express named human-gated sub-steps via existing sub_stages field (no schema change)
key-files:
  created:
    - tests/contracts/test_phase5_edit_gates.py
    - .planning/phases/HF-05-raw-edit-review-gates/deferred-items.md
  modified:
    - pipeline_defs/talking-head.yaml
    - pipeline_defs/podcast-repurpose.yaml
    - skills/meta/checkpoint-protocol.md
decisions:
  - Screen-demo scoped OUT (captured screen footage, not a raw-filler cut-list flow)
  - Two pre-existing broken manifests deferred, not fixed (out of scope, schema frozen)
metrics:
  tasks: 2
  files_changed: 5
  completed: 2026-07-25
status: complete
requirements: [EDITGATE-01, EDITGATE-02]
---

# Phase 5 Plan 05-01: Raw-Edit Named Review Gates Summary

Made the raw-footage edit flow an explicit, named, human-gated sequence
(`trim_filler -> approve_cut_list -> animate`) on the two raw-footage pipelines using the
existing `sub_stages` manifest field -- no schema change -- and documented the mandatory
cut-list approval gate in `checkpoint-protocol.md`.

## What Was Built

**Task 1 (tracer) -- talking-head gates + test**
- Added `sub_stages` to the `talking-head.yaml` `edit` stage: `trim_filler`
  (tools_available: silence_cutter, video_trimmer), `approve_cut_list`
  (`human_approval_default: true`, the named human gate), `animate` (post-approval).
- Flipped the `edit` stage-level `human_approval_default` from `false` to `true` (D-02).
- Created `tests/contracts/test_phase5_edit_gates.py`: asserts the three named sub_stages
  exist in order, `approve_cut_list.human_approval_default is True`, the stage requires
  human approval, and a no-regression guard that fails if the change breaks any
  previously-valid manifest.
- Tracer DoD met: `talking-head` load-validates GREEN + assertions pass (committed 04f7e08).

**Task 2 (expansion) -- podcast-repurpose + checkpoint-protocol + sweep**
- Applied the same three `sub_stages` and `human_approval_default: true` to the
  `podcast-repurpose.yaml` `edit` stage.
- Added the **Raw-Edit Cut-List Gate (Pre-Compose, Mandatory)** section to
  `skills/meta/checkpoint-protocol.md`: the gate sequence, that `approve_cut_list` is a
  MANDATORY human-approval gate before compose/animate render spend, how the protocol reads
  a sub-stage's `human_approval_default` (defaults true when omitted), and a sub-stage
  action table -- consistent with the existing protocol table and the Phase-3 Beat-Timeline
  gate section.
- Extended the test with a `podcast-repurpose` gate-assertion class (committed 3b344c6).

## Verification (Definition of Done)

- talking-head + podcast-repurpose `edit` stages express the named
  `trim_filler -> approve_cut_list -> animate` gates; `approve_cut_list` requires human
  approval: **PASS** (12/12 phase tests GREEN).
- checkpoint-protocol.md documents the raw-edit cut-list gate: **PASS**.
- New test GREEN; ASCII-clean added lines: **PASS** (all lines I added are ASCII; the only
  non-ASCII chars in edited files are pre-existing en/em-dashes I did not touch).
- Regression: `tests/contracts/test_phase3_contracts.py` (guards checkpoint-protocol
  required sections) + phase5 = **75 passed**.

## Scope Decisions

- **screen-demo scoped OUT.** Its `edit` stage edits captured screen footage (zoom-crop
  notes, dead-time trim/speed-up), not raw spoken footage with a filler cut-list that needs
  human sign-off before render spend. Per D-01 the raw-footage pipelines are exactly
  talking-head + podcast-repurpose. Documented in `deferred-items.md`.

## Deferred Issues (out of scope, pre-existing)

Two manifests already fail schema validation on the pre-HF-05 tree, for reasons unrelated
to the raw-edit gates. The schema is a hard constraint (must not edit), and no Python code
consumes the offending fields, so they are logged in `deferred-items.md` and NOT fixed:

1. `pipeline_defs/documentary-montage.yaml` -- `category: documentary` not in the schema
   enum. Fix (future): change value to `custom` or add `documentary` to the enum.
2. `pipeline_defs/screen-demo.yaml` -- top-level `production_modes` not permitted
   (`additionalProperties: false`). Fix (future): relocate under `metadata`.

The literal "every manifest load-validates" sweep therefore reports these two failures.
This plan introduced **zero** new breakage; the no-regression guard
(`test_no_new_manifest_breakage`) allowlists exactly these two and stays GREEN, so any NEW
breakage would still fail the test.

## Deviations from Plan

**1. [Rule 3 - Blocking] No-regression guard instead of a raw all-manifests-valid assert**
- **Found during:** Task 1 verification.
- **Issue:** The plan's "load-validate EVERY manifest" sweep is blocked by two pre-existing
  broken manifests (documentary-montage, screen-demo) unrelated to this phase.
- **Resolution:** Kept the test GREEN and in-scope by asserting no NEW breakage against a
  known-preexisting allowlist, and asserting the two target pipelines validate. Logged the
  two defects to `deferred-items.md`. Did not fix them (out of scope; schema frozen; fields
  are inert w.r.t. code).
- **Files:** tests/contracts/test_phase5_edit_gates.py, deferred-items.md.
- **Commits:** 04f7e08, 3b344c6.

## Commits
- 04f7e08: feat(05-01): name raw-edit gates on talking-head + tracer test
- 3b344c6: feat(05-01): raw-edit gates on podcast-repurpose + checkpoint-protocol doc

## Known Stubs
None.

## Self-Check: PASSED
All 5 created/modified files present; commits 04f7e08 + 3b344c6 verified in git log.
