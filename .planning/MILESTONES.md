# Milestones

Pre-GSD history (the platform existed and shipped before GSD tracking was added).
Baseline captured 2026-07-20 so the hyperframes port can run as a tracked milestone.

## Shipped before GSD (baseline — v0.x)

- Instruction-driven pipeline engine (13 `pipeline_defs/` manifests, director + meta skills).
- Capability-first tool families: `tts_selector`, `video_selector`, and providers.
- Screen-demo `real_capture` pipeline + Remotion overlay pass.
- `client-doc-walkthrough-video` skill (narrated client-HTML walkthroughs).
- ElevenLabs voice cloning with accent-safe spliced-pause prosody.
- Piper local TTS provider.
- FastAPI service + `openmontage` MCP server; 3-credential auth.
- hyperframes engine vendored (`.agents/skills/hyperframes/`, `hyperframes_compose.py`).

## In progress

- **v1.0 HF-PORT** — Hyperframes creative-doctrine + Kokoro local TTS + per-project
  storyboard/brand-lock conventions + raw-edit review gates. See PROJECT.md.
