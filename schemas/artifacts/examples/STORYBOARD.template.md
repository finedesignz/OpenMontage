# Storyboard Convention (STORYBOARD.md)

`STORYBOARD.md` is the human-readable rendering of the `storyboard` artifact
(`schemas/artifacts/storyboard.schema.json`). One lives per project at
`projects/<name>/STORYBOARD.md`. It is what the human reviews at the beat-timeline
approval gate, BEFORE the `assets` stage spends on generation or render.

The machine artifact (`storyboard.json`) is the source of truth; this Markdown is a
faithful, read-at-a-glance rendering of the same beats. Keep them in sync.

## How to author

1. Author the `storyboard` artifact first (validate against the schema).
2. Render it to `STORYBOARD.md` using the template below, one row per beat.
3. Present `STORYBOARD.md` to the human for approval at the `scene_plan` gate.
4. On approval, proceed to `assets`. On revision, edit the artifact and re-render.

Rules:
- ASCII-only punctuation (hyphens, straight quotes, three dots for ellipsis).
- Every beat in the artifact appears as exactly one row, in start order.
- `start` and `dur` are seconds and must match the artifact.
- SFX and music-duck cells list the per-beat cues as `at_seconds: value`.

## Template

```markdown
# Storyboard - <project name>

- Total: <total_seconds>s
- Music bed: <music_bed or "none">

| # | Beat | Start | Dur | On screen | VO | SFX | Music duck |
|---|------|-------|-----|-----------|----|-----|-----------|
| 1 | <id> | 0.0 | 4.0 | <on_screen> | <vo> | 0.2: soft_whoosh | 0.0: -6 dB (intro) |
| 2 | <id> | 4.0 | 5.0 | <on_screen> | <vo> | - | 0.0: -18 dB (duck under VO) |
| 3 | <id> | 9.0 | 3.0 | <on_screen> | <vo> | - | 2.5: -6 dB (restore for outro) |

Approve to continue to asset generation, or request revisions to any beat.
```
