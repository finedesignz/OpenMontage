# Phase 4: Brand Lock - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Phase Boundary
Add a brand-lock DESIGN contract (a brand-derived LOCKED palette + type/logo with an
explicitly VARIED motion vocabulary) expressible within OM's style-playbook system, and a
style-philosophy OVERRIDE mechanism layered on `styles/*.yaml` that swaps the look
(motion/composition/texture/pacing) while the locked brand fields always win. Delivers
BRAND-01/02. Extends the existing playbook schema + `playbook_loader.py` — no new system.
</domain>

<decisions>
## Implementation Decisions
- **D-01 (BRAND-01):** Add an OPTIONAL `brand_lock` block to
  `schemas/styles/playbook.schema.json` (schema stays backward-compatible — existing
  playbooks without it still validate). Shape: `{locked: true, palette: {primary[],
  accent[], background, text}, typography?: {...}, logo?: {path/text}, source?: url}` —
  the brand-derived, non-overridable identity. Document that the LOCK applies to palette +
  type/logo; motion vocabulary is deliberately left free/varied.
  — Reversibility: reversible (additive optional field).
- **D-02 (BRAND-02):** Add `apply_philosophy(base: dict, overlay: dict) -> dict` to
  `styles/playbook_loader.py`: a deterministic merge where the overlay (a "style
  philosophy" — e.g. minimalist / soft / brutalist) replaces the LOOK sections
  (`motion`, `visual_language.composition`, `visual_language.texture`, pacing) but any
  field under `brand_lock` (and the locked palette/type it names) is preserved verbatim —
  overlay attempts to change locked brand fields are ignored/rejected. Result re-validates
  against the schema. — Reversibility: costly (a merge contract other code will rely on).
- **D-03:** Ship a worked example: one brand-locked base playbook
  (`styles/example-brand-lock.yaml`) + a philosophy overlay
  (`styles/philosophies/<name>.yaml` or documented inline) + a test proving
  `apply_philosophy` swaps motion but preserves the locked palette.

### Claude's Discretion
- Exact overlay file location/format; whether overlays are full partial-playbooks or a
  thin `{philosophy, motion, composition, texture, pace}` doc. Follow house convention.
- Whether a locked-field-violation is a hard error or a silent no-op (pick the safer:
  reject with a clear message).

## Deferred Ideas
- Auto-deriving the locked palette from a brand URL/logo (client-brand-extract already
  exists as a skill) — wire-up is a future phase.
</decisions>

## Downstream Notes
- Verify: schema still validates all existing `styles/*.yaml`; the new brand-lock example
  validates; `apply_philosophy(base, overlay)` returns a schema-valid playbook whose
  `motion` came from the overlay but whose `brand_lock`/locked palette is byte-identical to
  base; a locked-field override attempt is rejected/ignored; tests GREEN; ASCII-clean.
