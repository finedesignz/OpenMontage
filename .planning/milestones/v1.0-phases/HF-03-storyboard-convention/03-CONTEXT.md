# Phase 3: Storyboard Convention - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Phase Boundary
Add a per-project **STORYBOARD** artifact (reviewable beat timeline with per-beat
duration, per-timestamp SFX cues, music-duck points) + JSON schema, a per-project
**meta.json** convention, and a **beat-timeline human-approval gate** in the screen-demo
(and explainer) pipelines so the human approves the beat timeline BEFORE asset gen /
render spend. Delivers STORY-01/02/03. Maps onto OM's existing artifact-schema +
checkpoint-protocol + `projects/<name>/` constructs — no new orchestrator.
</domain>

<decisions>
## Implementation Decisions
- **D-01 (STORY-01):** Canonical machine artifact `storyboard` + schema
  `schemas/artifacts/storyboard.schema.json` (JSON draft 2020-12, `$id`
  `openmontage/artifacts/storyboard`, `version` const "1.0", mirror the house style of
  `scene_plan.schema.json`/`edit_decisions.schema.json`). Shape: `beats[]` each with
  `id`, `start_seconds`, `duration_seconds`, `label`/`on_screen`, optional `vo` line,
  `sfx[]` (each `{at_seconds, cue}`), and `music` duck points (`{at_seconds, level_db,
  reason}`); plus top-level `music_bed` + `total_seconds`. A human-readable `STORYBOARD.md`
  is the review rendering of that artifact (a template + convention, one per project).
- **D-02 (STORY-02):** `project_meta` convention = a `meta.json` at `projects/<name>/`
  capturing project-level audio/render settings (fps, resolution, voice_id/provider,
  music_bed, room_tone_dbfs, target aspect). Add `schemas/artifacts/project_meta.schema.json`
  and document the convention; provide a filled example. Reversibility: reversible (additive).
- **D-03 (STORY-03):** The gate is the existing checkpoint mechanism, not new code: in
  `pipeline_defs/screen-demo.yaml` (and `animated-explainer.yaml`) set the beat-timeline
  stage (`scene_plan`) to `checkpoint_required: true` + `human_approval_default: true` and
  have it `produces: storyboard`, so approval is forced BEFORE the `assets` stage spends.
  Add a short section to `skills/meta/checkpoint-protocol.md` naming the beat-timeline /
  storyboard as a mandatory pre-asset human-approval gate. — Reversibility: costly
  (changes a pipeline's default human-gate behavior; documented contract).

### Claude's Discretion
- Exact field names within a beat; whether STORYBOARD.md is a `styles/`-style template or
  a director-embedded convention (planner picks, following house convention).

## Deferred Ideas
- Auto-render STORYBOARD.md from storyboard.json — nice-to-have, not this phase.
</decisions>

## Downstream Notes
- Verify: both schemas exist + validate (draft 2020-12, parse-clean); an example
  storyboard + meta.json validate against them; screen-demo + explainer scene_plan stage
  carries the human-approval gate + `produces: storyboard`; checkpoint-protocol documents
  the gate; ASCII-clean.
