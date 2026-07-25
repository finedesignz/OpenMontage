# Deferred Items -- HF-05 Raw-Edit Review Gates

Out-of-scope defects discovered during HF-05 execution. NOT caused by this phase's
changes (this phase only touched the `edit` stage of talking-head + podcast-repurpose,
skills/meta/checkpoint-protocol.md, and tests). Recorded per the executor scope boundary.

## Pre-existing manifest schema violations

These two manifests already fail `lib.pipeline_loader.load_pipeline()` validation against
`schemas/pipelines/pipeline_manifest.schema.json` on the pre-HF-05 tree. The schema is a
hard constraint for HF-05 (must not edit it), so these are left for a follow-up.

1. **pipeline_defs/documentary-montage.yaml** -- `category: documentary` is not in the
   schema enum `[talking_head, generated, hybrid, screen_recording, animation, cinematic,
   custom]`. Fix options: change the manifest value to `custom` (or the closest fitting
   enum), or (separate schema phase) add `documentary` to the enum.

2. **pipeline_defs/screen-demo.yaml** -- top-level property `production_modes` is not
   permitted (`additionalProperties: false` at the manifest root). Fix options: relocate
   `production_modes` under `metadata`, or model it explicitly in a future schema phase.

The HF-05 no-regression guard (`tests/contracts/test_phase5_edit_gates.py`
::`test_no_new_manifest_breakage`) allowlists exactly these two so it stays GREEN while
still catching any NEW breakage introduced by the gate change.
