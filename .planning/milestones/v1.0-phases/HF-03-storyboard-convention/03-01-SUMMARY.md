---
phase: 3
plan: "03-01"
subsystem: artifact-schemas
status: complete
tags: [schema, storyboard, project_meta, checkpoint-gate, pipeline-manifest]
requires: [scene_plan schema, checkpoint-protocol skill]
provides:
  - storyboard artifact + schema
  - project_meta artifact + schema
  - beat-timeline pre-asset human-approval gate
affects:
  - pipeline_defs/screen-demo.yaml
  - pipeline_defs/animated-explainer.yaml
  - skills/meta/checkpoint-protocol.md
tech-stack:
  added: []
  patterns: [json-schema-draft-2020-12, additionalProperties-false, artifact-registry]
key-files:
  created:
    - schemas/artifacts/storyboard.schema.json
    - schemas/artifacts/project_meta.schema.json
    - schemas/artifacts/examples/storyboard.example.json
    - schemas/artifacts/examples/project_meta.example.json
    - schemas/artifacts/examples/STORYBOARD.template.md
  modified:
    - schemas/artifacts/__init__.py
    - pipeline_defs/screen-demo.yaml
    - pipeline_defs/animated-explainer.yaml
    - skills/meta/checkpoint-protocol.md
decisions:
  - STORYBOARD.md convention lives as a template file co-located with schema examples (schemas/artifacts/examples/STORYBOARD.template.md) rather than a styles/ playbook, since it renders an artifact not a visual style.
  - scene_plan is the beat-timeline stage; both manifests already carried the checkpoint flags, so the gate only needed storyboard added to produces.
metrics:
  duration: ~15m
  completed: 2026-07-24
  tasks: 2
  files: 9
---

# Phase 3 Plan 03-01: Storyboard + meta.json convention + beat-timeline approval gate Summary

Added two canonical artifact schemas (`storyboard`, `project_meta`, JSON draft 2020-12, `$id` `openmontage/artifacts/<name>`, `version` const "1.0", `additionalProperties: false` mirroring the house style of `scene_plan`/`edit_decisions`), registered both in the artifact registry, and wired the existing checkpoint mechanism into a mandatory pre-asset beat-timeline human-approval gate on the `scene_plan` stage of both the screen-demo and animated-explainer pipelines.

## What was built

### Task 1 (tracer) - storyboard schema + validated example
- `schemas/artifacts/storyboard.schema.json`: top-level `version` const, `total_seconds`, optional `music_bed`, and `beats[]` where each beat = `{id, start_seconds, duration_seconds, on_screen, vo?, sfx?:[{at_seconds,cue}], music?:[{at_seconds,level_db,reason}]}`. All objects `additionalProperties: false`.
- Registered `storyboard` in `ARTIFACT_NAMES` (`schemas/artifacts/__init__.py`).
- `schemas/artifacts/examples/storyboard.example.json`: a 12s, 3-beat example (logo bumper / doctor scene / offer card) that validates GREEN against the schema via `jsonschema` draft 2020-12 and via the repo's `validate_artifact("storyboard", ...)`.
- Tracer gate verified end-to-end before expansion: `Draft202012Validator.check_schema` passes, example validates, `storyboard` is discoverable via `list_schemas()`.

### Task 2 (expansion) - meta.json + STORYBOARD convention + the gate
- `schemas/artifacts/project_meta.schema.json`: `{version const, fps, resolution:{w,h}, aspect?, tts:{provider,voice_id}, music_bed?, room_tone_dbfs?}`. Registered in `__init__.py`.
- `schemas/artifacts/examples/project_meta.example.json`: filled 1920x1080@30 / elevenlabs example that validates GREEN; matches the `projects/<name>/` shape (music bed path, room-tone floor).
- `schemas/artifacts/examples/STORYBOARD.template.md`: the human-readable rendering convention + how-to-author note + a one-row-per-beat Markdown table template. This is what the human reviews at the gate.
- Beat-timeline gate: added `storyboard` to `produces` on the `scene_plan` stage of both `pipeline_defs/screen-demo.yaml` and `pipeline_defs/animated-explainer.yaml`. Both stages already carried `checkpoint_required: true` + `human_approval_default: true`, so approval is forced BEFORE the `assets` stage spends.
- `skills/meta/checkpoint-protocol.md`: new "Beat-Timeline / Storyboard Gate (Pre-Asset, Mandatory)" section with a policy table consistent with the existing Sample Checkpoint format, naming the storyboard as a mandatory pre-asset approval gate.

## Verification

- Both schemas parse as valid draft 2020-12 (`check_schema`) and both examples validate GREEN, both via `jsonschema` directly and via `validate_artifact()`.
- Both YAML manifests `yaml.safe_load` clean; asserted `scene_plan` stage has `checkpoint_required: true`, `human_approval_default: true`, and `storyboard` in `produces` on both.
- `storyboard` and `project_meta` both discoverable via `list_schemas()`.
- All newly added / edited lines are ASCII-clean (verified via `git diff` added-line scan).

## Deviations from Plan

None - plan executed as written. The `scene_plan` stages already had the checkpoint flags set (from prior phases), so the gate wiring reduced to adding `storyboard` to `produces` plus documenting the gate; no flag changes were needed.

## Known Stubs

None. No hardcoded empty values, placeholders, or TODOs introduced.

## Out-of-scope observations (not fixed - pre-existing)

The ASCII-clean scan flagged pre-existing non-ASCII characters in lines this plan did NOT touch: box-drawing comment banners (`0x2500`) in `animated-explainer.yaml` lines 61/115, and em-dashes (`0x2014`) in the original prose of `checkpoint-protocol.md`, `screen-demo.yaml`, and `animated-explainer.yaml`. Per the executor scope boundary these were left untouched (not caused by this task). Logged here for a future ASCII sweep if desired.

## Self-Check: PASSED

All 5 created artifacts + SUMMARY.md exist on disk; both task commits (9bf26c4, 22d22e6) present in git log.
