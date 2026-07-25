# Phase 5: Raw-Edit Review Gates - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Phase Boundary
Make the raw-footage edit flow an explicit, named, human-gated sequence
(trim-filler -> approve-cut-list -> animate) in the pipelines that edit raw footage, and
enforce the cut-list gate through `checkpoint-protocol.md`. Delivers EDITGATE-01/02.
Uses the EXISTING `sub_stages` field on the pipeline-manifest stage schema -- no schema
change, no new orchestrator.
</domain>

<decisions>
## Implementation Decisions
- **D-01 (EDITGATE-01):** Express the named gates as `sub_stages` on the `edit` stage of the
  raw-footage pipelines `talking-head.yaml` and `podcast-repurpose.yaml` (both transcribe raw
  footage and produce `edit_decisions` = the cut list). The stage schema already permits
  `sub_stages` with `{name, description, condition, human_approval_default, tools_available,
  review_focus}` -- so NO schema edit. Sub-stages:
  - `trim_filler` -- auto jump-cuts / filler removal (tools_available: silence_cutter,
    video_trimmer).
  - `approve_cut_list` -- `human_approval_default: true`; the named HUMAN gate; review_focus
    = the cut list (edit_decisions) is correct before any render spend.
  - `animate` -- proceed to compose/animate only after approval.
- **D-02:** Flip the `edit` stage's `human_approval_default` to `true` on these pipelines
  (currently `false` on talking-head) so the cut list is not finalized without human sign-off.
  — Reversibility: costly (changes a pipeline's default human-gate behavior; documented).
- **D-03 (EDITGATE-02):** Add a section to `skills/meta/checkpoint-protocol.md` defining the
  raw-edit gate sequence and that `approve_cut_list` is a MANDATORY human-approval gate
  before the compose/animate spend -- and how the protocol reads a sub-stage's
  `human_approval_default`. Consistent with the existing protocol table + the beat-timeline
  gate added in Phase 3.

### Claude's Discretion
- Whether to also wire the screen-demo edit stage (it edits captured footage) -- include only
  if it has a raw-trim step; otherwise scope to talking-head + podcast-repurpose.
- Exact sub_stage descriptions / review_focus wording.

## Deferred Ideas
- A tool that auto-generates the cut list diff for the human to approve -- future.
</decisions>

## Downstream Notes
- Verify: `talking-head.yaml` + `podcast-repurpose.yaml` load-validate via
  `lib/pipeline_loader.py`; their `edit` stage has the three named sub_stages with
  `approve_cut_list.human_approval_default == true`; checkpoint-protocol documents the gate;
  ASCII-clean; no other manifest broken.
