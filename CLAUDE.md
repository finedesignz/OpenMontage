<!-- template-version: 1 -->
<!-- repo-align-template: dev v1 -->

# OpenMontage

**MANDATORY: Read [`AGENT_GUIDE.md`](AGENT_GUIDE.md) before responding to ANY user message.**

Do not act on the user's request until you have read AGENT_GUIDE.md.
It contains routing rules that determine your first action based on what the user asked.
Skipping it WILL cause you to take the wrong action.

There are no production/workflow instructions in this file beyond the pointer above — all
pipeline/skill/agent routing instructions live in `AGENT_GUIDE.md`. The sections below are
the repo-align standard sections for orientation; they don't replace AGENT_GUIDE.md.

## Purpose

Instruction-driven AI video production system. The agent reads pipeline manifests
(`pipeline_defs/*.yaml`) plus stage-director skills (`skills/pipelines/<pipeline>/`) and
drives production tools (Python `BaseTool` subclasses) stage by stage, with checkpoints and
human review. See `AGENT_GUIDE.md` for the full operating contract (Rule Zero: all
production goes through a pipeline, no ad-hoc script calls).

## Stack

Python backend (`api/`, `tools/`) exposing production tools; large `.agents/skills/`
library of provider-specific prompting/skill docs (ElevenLabs, Flux, HeyGen avatar video,
D3, ffmpeg, etc.). Tests under `tests/`.

## API key handling (verified, not a rule-22c violation)

- `OPENAI_API_KEY` is a legitimate end-user-supplied **provider** key for OpenAI media
  products (DALL-E image gen via `tools/graphics/openai_image.py`, TTS via
  `tools/audio/openai_tts.py`) — same category as `FAL_KEY`, `RUNWAY_API_KEY`,
  `KLING_API_KEY`, `REPLICATE_API_TOKEN` used elsewhere in `tools/`. These are the actual
  product being orchestrated, not a substitute for our own LLM/agent calls.
- `ANTHROPIC_API_KEY` is explicitly **defended against**, not used: `api/agent_auth.py`
  and `api/runner.py` strip `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` /
  `ANTHROPIC_AUTH_TOKEN` from the subprocess environment before invoking Claude Code, so a
  stray key in the shell can't silently switch billing off the subscription. This is
  rule-22c enforced in code, the opposite of a violation.

## Commands

No CI workflow present on `origin/main` (`.github/workflows/` and `.woodpecker/` both
absent) — confirm with the owner before assuming test/lint commands; check `tests/`
directly for pytest usage if you need to run the suite locally.

## Deploy target

Not established in this pass — no CI/deploy config found on `origin/main`.

## Repo conventions

Pipeline manifests: `pipeline_defs/*.yaml`. Stage-director skills:
`skills/pipelines/<pipeline>/<stage>-director.md`. Provider prompting skills:
`.agents/skills/<provider>/SKILL.md`. Meta skills (onboarding, reference-video analysis):
`skills/meta/`. Python holds tools + persistence only — no orchestration/creative/review
logic belongs there per `AGENT_GUIDE.md`.

## GSD state

No `.planning/` directory found on `origin/main` in this pass — not currently on GSD.

## Gotchas

- Never bypass the pipeline system with ad-hoc Python calling tools directly — see Rule
  Zero in `AGENT_GUIDE.md`.
- When both Remotion and HyperFrames render runtimes are available, both MUST be presented
  to the user before locking `render_runtime` — silently defaulting is a documented
  CRITICAL reviewer finding.
