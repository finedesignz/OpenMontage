"""Tests for the brand-lock contract + style-philosophy override (Phase HF-04).

Proves BRAND-01/BRAND-02:
  * the optional ``brand_lock`` schema block is backward-compatible -- every
    shipped ``styles/*.yaml`` still loads and validates (TASK 1, D-01);
  * a brand-locked base playbook validates;
  * ``apply_philosophy(base, overlay)`` swaps the LOOK sections (motion,
    composition, texture, pace) to the overlay's while the locked ``brand_lock``
    block and the palette it names stay byte-identical (BRAND-02, D-02);
  * an overlay that tries to change a locked field is REJECTED with a clear
    error (the safe behavior chosen in CONTEXT D-02).

No network or filesystem writes -- pure schema/dict-merge surface.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from styles.playbook_loader import (
    apply_philosophy,
    list_playbooks,
    load_philosophy,
    load_playbook,
    validate_playbook,
)

STYLES_DIR = Path(__file__).resolve().parents[2] / "styles"


# ---------------------------------------------------------------------------
# Back-compat: every shipped playbook still validates under the updated schema
# ---------------------------------------------------------------------------

# anime-ghibli is a known-broken playbook against the strict schema and is
# deliberately excluded from validation, matching tests/qa/test_07_playbook_intelligence.py.
# brand_lock must not weaken the shared schema to accommodate it.
_STRICT_VALID_PLAYBOOKS = ["clean-professional", "flat-motion-graphics", "minimalist-diagram"]


def test_all_shipped_playbooks_still_validate():
    """brand_lock is optional -- adding it must not break any previously-valid style."""
    available = list_playbooks()
    assert available, "list_playbooks() returned nothing"
    for name in _STRICT_VALID_PLAYBOOKS:
        # load_playbook validates internally; a failure raises.
        load_playbook(name)


@pytest.mark.parametrize("name", _STRICT_VALID_PLAYBOOKS)
def test_named_legacy_playbooks_validate(name):
    """The playbooks valid before brand_lock must still validate after it."""
    assert name in list_playbooks()
    load_playbook(name)


# ---------------------------------------------------------------------------
# A brand-locked base playbook validates
# ---------------------------------------------------------------------------

def test_example_brand_lock_playbook_validates():
    pb = load_playbook("example-brand-lock")
    assert pb["brand_lock"]["locked"] is True
    assert "palette" in pb["brand_lock"]


# ---------------------------------------------------------------------------
# apply_philosophy swaps the look but preserves the locked brand identity
# ---------------------------------------------------------------------------

def _minimalist_overlay() -> dict:
    return {
        "philosophy": "minimalist",
        "motion": {
            "transitions": ["cut", "fade"],
            "animation_style": "linear, no easing, austere",
            "pacing_rules": {
                "min_scene_hold_seconds": 4.0,
                "max_scene_hold_seconds": 10,
                "text_card_hold_seconds": 5,
                "stat_card_hold_seconds": 4,
                "transition_duration_seconds": 0.2,
            },
            "entrance": "hard cut",
            "exit": "hard cut",
        },
        "visual_language": {
            "composition": "extreme negative space, single focal point, hard grid",
            "texture": "flat, matte, zero grain",
        },
        "pace": "deliberate",
    }


def test_apply_philosophy_swaps_look():
    base = load_playbook("example-brand-lock")
    overlay = _minimalist_overlay()

    merged = apply_philosophy(base, overlay)

    # Result is schema-valid (apply_philosophy re-validates before returning).
    validate_playbook(merged)

    # LOOK sections came from the overlay.
    assert merged["motion"] == overlay["motion"]
    assert merged["visual_language"]["composition"] == overlay["visual_language"]["composition"]
    assert merged["visual_language"]["texture"] == overlay["visual_language"]["texture"]
    assert merged["identity"]["pace"] == overlay["pace"]


def test_apply_philosophy_preserves_locked_brand_byte_identical():
    base = load_playbook("example-brand-lock")
    overlay = _minimalist_overlay()

    merged = apply_philosophy(base, overlay)

    # brand_lock block and the locked palette are byte-identical to base.
    assert merged["brand_lock"] == base["brand_lock"]
    assert merged["visual_language"]["color_palette"] == base["visual_language"]["color_palette"]
    # typography named by the lock is preserved.
    assert merged["typography"] == base["typography"]


def test_apply_philosophy_does_not_mutate_inputs():
    base = load_playbook("example-brand-lock")
    base_snapshot = copy.deepcopy(base)
    overlay = _minimalist_overlay()
    overlay_snapshot = copy.deepcopy(overlay)

    apply_philosophy(base, overlay)

    assert base == base_snapshot, "apply_philosophy mutated the base playbook"
    assert overlay == overlay_snapshot, "apply_philosophy mutated the overlay"


# ---------------------------------------------------------------------------
# Locked-field override is rejected with a clear error (safe behavior)
# ---------------------------------------------------------------------------

def test_overlay_changing_locked_palette_is_rejected():
    base = load_playbook("example-brand-lock")
    bad = _minimalist_overlay()
    bad["visual_language"]["color_palette"] = {
        "primary": ["#000000"],
        "accent": ["#FFFFFF"],
        "background": "#111111",
        "text": "#EEEEEE",
    }
    with pytest.raises(ValueError):
        apply_philosophy(base, bad)


def test_overlay_touching_brand_lock_is_rejected():
    base = load_playbook("example-brand-lock")
    bad = _minimalist_overlay()
    bad["brand_lock"] = {"locked": True, "palette": {"primary": ["#000000"]}}
    with pytest.raises(ValueError):
        apply_philosophy(base, bad)


def test_overlay_changing_locked_typography_is_rejected():
    base = load_playbook("example-brand-lock")
    bad = _minimalist_overlay()
    bad["typography"] = {"headings": {"font": "Comic Sans"}, "body": {"font": "Comic Sans"}}
    with pytest.raises(ValueError):
        apply_philosophy(base, bad)


def test_overlay_unknown_top_level_key_is_rejected():
    base = load_playbook("example-brand-lock")
    bad = _minimalist_overlay()
    bad["audio"] = {"voice_style": "x", "music_mood": "y", "music_volume": 0.1}
    with pytest.raises(ValueError):
        apply_philosophy(base, bad)


# ---------------------------------------------------------------------------
# TASK 2: a real philosophy overlay file swaps look, keeps locked palette
# ---------------------------------------------------------------------------

def test_minimalist_philosophy_file_swaps_look_keeps_palette():
    base = load_playbook("example-brand-lock")
    overlay = load_philosophy("minimalist")

    merged = apply_philosophy(base, overlay)
    validate_playbook(merged)

    # Motion/composition/texture swapped to the overlay's values.
    assert merged["motion"] == overlay["motion"]
    assert merged["visual_language"]["composition"] == overlay["visual_language"]["composition"]
    assert merged["visual_language"]["texture"] == overlay["visual_language"]["texture"]

    # Locked brand palette unchanged.
    assert merged["visual_language"]["color_palette"] == base["visual_language"]["color_palette"]
    assert merged["brand_lock"] == base["brand_lock"]


def test_apply_philosophy_idempotent_on_locked_fields():
    """Applying the overlay twice yields the same locked brand identity."""
    base = load_playbook("example-brand-lock")
    overlay = load_philosophy("minimalist")

    once = apply_philosophy(base, overlay)
    twice = apply_philosophy(once, overlay)

    assert twice["brand_lock"] == base["brand_lock"]
    assert twice["visual_language"]["color_palette"] == base["visual_language"]["color_palette"]
    assert twice["motion"] == once["motion"]
