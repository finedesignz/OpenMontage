"""Phase 5 contract tests -- raw-edit named review gates.

Verifies that the raw-footage pipelines (talking-head, podcast-repurpose) express
the named edit sub-stages (trim_filler -> approve_cut_list -> animate) with the
mandatory human-approval gate on approve_cut_list, that the edit stage itself flips
to human_approval_default true, and that EVERY manifest still load-validates.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.pipeline_loader import (  # noqa: E402
    load_pipeline,
    list_pipelines,
    get_stage_sub_stages,
)

RAW_EDIT_PIPELINES = ["talking-head", "podcast-repurpose"]
EXPECTED_SUB_STAGES = ["trim_filler", "approve_cut_list", "animate"]

# Manifests already invalid against the frozen schema BEFORE this phase, for reasons
# unrelated to the raw-edit gates (documentary-montage: category 'documentary' not in
# the schema enum; screen-demo: top-level 'production_modes' not permitted). Tracked in
# .planning/phases/HF-05-raw-edit-review-gates/deferred-items.md. Listed here so the
# no-regression guard below stays GREEN while still catching any NEW breakage this
# phase might introduce.
KNOWN_PREEXISTING_INVALID = {"documentary-montage", "screen-demo"}


def _edit_stage(manifest: dict) -> dict:
    for stage in manifest["stages"]:
        if stage["name"] == "edit":
            return stage
    raise AssertionError(f"Manifest {manifest.get('name')!r} has no edit stage")


class TestTalkingHeadEditGates:
    """Tracer: talking-head names the gates and still validates."""

    def test_loads_and_validates(self):
        manifest = load_pipeline("talking-head")
        assert manifest["name"] == "talking-head"

    def test_edit_stage_requires_human_approval(self):
        manifest = load_pipeline("talking-head")
        assert _edit_stage(manifest).get("human_approval_default") is True

    def test_named_sub_stages_present_in_order(self):
        manifest = load_pipeline("talking-head")
        names = [s["name"] for s in get_stage_sub_stages(manifest, "edit")]
        assert names == EXPECTED_SUB_STAGES

    def test_approve_cut_list_is_the_human_gate(self):
        manifest = load_pipeline("talking-head")
        subs = {s["name"]: s for s in get_stage_sub_stages(manifest, "edit")}
        assert subs["approve_cut_list"]["human_approval_default"] is True

    def test_trim_filler_has_cut_tools(self):
        manifest = load_pipeline("talking-head")
        subs = {s["name"]: s for s in get_stage_sub_stages(manifest, "edit")}
        tools = subs["trim_filler"].get("tools_available", [])
        assert "silence_cutter" in tools
        assert "video_trimmer" in tools


class TestAllManifestsStillValidate:
    """The edit-gate change must not break any previously-valid manifest."""

    def test_no_new_manifest_breakage(self):
        failed = set()
        for name in list_pipelines():
            try:
                load_pipeline(name)
            except Exception:  # jsonschema.ValidationError or load error
                failed.add(name)
        new_breakage = failed - KNOWN_PREEXISTING_INVALID
        assert not new_breakage, (
            f"Edit-gate change broke previously-valid manifests: {sorted(new_breakage)}"
        )

    @pytest.mark.parametrize("name", RAW_EDIT_PIPELINES)
    def test_target_pipelines_validate(self, name):
        manifest = load_pipeline(name)
        assert manifest["name"] == name
        assert manifest["stages"]
