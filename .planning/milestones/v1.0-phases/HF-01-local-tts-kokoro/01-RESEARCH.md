# Phase 1: Local TTS (Kokoro) - Research

**Researched:** 2026-07-22
**Domain:** Offline neural TTS provider integration (Kokoro-82M) into OpenMontage's BaseTool/`tts_selector` pattern
**Confidence:** HIGH (package, model, license, selector mechanics all verified this session)

## Summary

Kokoro-82M is an 82M-param, Apache-2.0 neural TTS model with 54 voices across 8 languages. The
clean offline/CPU path on this Windows host is the **`kokoro-onnx`** package (ONNX Runtime, no
PyTorch). Its 0.5.0 release bundles espeak-ng through `espeakng-loader`, which **eliminates the
usual Windows espeak-ng-install gotcha** — the phonemizer backend ships as a wheel dependency, no
system install, no PATH surgery. Inference is fully offline once two model files
(`kokoro-v1.0.onnx` ~310 MB, `voices-v1.0.bin` ~27 MB) are downloaded once from the package's
GitHub release.

The `tts_selector` auto-discovers any `capability="tts"` BaseTool, so `kokoro_tts` needs **zero
selector edit for discovery** (D-01 confirmed). Precedence (D-05) is **not** hardcoded anywhere —
the selector ranks providers via `lib/scoring.py`'s weighted score. Kokoro is ordered above Piper
by setting one explicit lever: `quality_score`. The "don't silently downgrade a requested paid
voice" contract is a **real gap in the current selector** (`_select_best_tool` falls through to the
free auto-path when an explicitly-requested provider is unavailable) and must be fixed in
lines 178-187.

**Primary recommendation:** Depend on `kokoro-onnx==0.5.0` + `soundfile`; mirror `piper_tts.py`
but set `runtime=LOCAL`, a Python import dependency (not `cmd:`), and `quality_score=0.7`; fix the
selector's explicit-preference fall-through; author a small `.agents/skills/kokoro/` Layer-3 skill
(the existing `text-to-speech` skill teaches HeyGen, not Kokoro).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `tools/audio/kokoro_tts.py` as a `BaseTool` mirroring `piper_tts.py` —
  `capability="tts"`, `provider="kokoro"`, `tier=VOICE`, `runtime=ToolRuntime.LOCAL`,
  `determinism=DETERMINISTIC`, `execution_mode=SYNC`. Selector auto-discovers — no discovery edit.
- **D-02:** `supports = {voice_cloning: False, multilingual: True, offline: True, native_audio: True}`;
  `best_for` reflects Kokoro's edge over Piper (54 voices, 8 langs, higher expressive quality, free/offline).
- **D-03:** Runs via `kokoro`/`kokoro-onnx` Python package (ONNX, CPU-capable), NOT a `cmd:` binary.
  `dependencies` declares the pip package; `install_instructions` gives pip install + model/voices
  download. Model+voices cache under a stable dir (`~/.kokoro`). Exact package/model id = research item (resolved below).
- **D-04:** `input_schema` mirrors Piper's shape (`text`, `voice`/`speaker`, `speed`/`length_scale`
  analog, `output_path`). `agent_skills = ["text-to-speech"]` at minimum; add a Kokoro engine
  reference under `.agents/skills/` OR reuse existing generic TTS skill (resolved below).
- **D-05:** Selector ordering for `preferred_provider="auto"`: ElevenLabs (if key + specific
  voice/clone requested) → **Kokoro** → **Piper** (last resort). An explicitly-requested paid
  voice/clone must NOT silently downgrade — surface "requested voice unavailable". Free-tier auto
  picks Kokoro over Piper. — Reversibility: costly (touches selector scoring + documented contract).
- **D-06:** Document precedence in selector docstring/metadata AND `PROJECT_CONTEXT.md`'s TTS bullet.

### Claude's Discretion
- Exact Kokoro package (`kokoro` vs `kokoro-onnx`), pinned model id, default voice — decide from
  current upstream; verify offline CPU path on this Windows host (GPU optional).
- Whether the engine skill is new or an existing `text-to-speech` skill suffices.

### Deferred Ideas (OUT OF SCOPE)
- Kokoro voice-cloning parity with ElevenLabs — Kokoro is synthesis-only; its own phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TTS-01 | Add `kokoro_tts` provider (BaseTool, mirror `piper_tts`), Kokoro-82M offline, 54 voices / 8 langs | Package + model + full field contract pinned below; 54/8/Apache-2.0 verified |
| TTS-02 | Register in `tts_selector` with cost=0 / offline status + `agent_skills[]` bridge to a `.agents/skills` engine ref | Auto-discovery confirmed; `estimate_cost`→0; existing `text-to-speech` skill is HeyGen-specific → author `.agents/skills/kokoro/` |
| TTS-03 | Define+document fallback precedence: narration with zero paid/dead-key dep, no silent downgrade of a requested voice | Precedence is score-driven (not hardcoded); `quality_score` lever + selector fix at lines 178-187 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `kokoro-onnx` | `==0.5.0` | Kokoro-82M inference via ONNX Runtime (CPU, offline) | No PyTorch; bundles espeak-ng via `espeakng-loader` (Windows-clean); the ONNX-first fork of Kokoro `[VERIFIED: PyPI JSON, released 2026-01-30]` |
| `soundfile` | `>=0.12` | Write the returned float32 samples to WAV | `kokoro.create()` returns `(samples: np.ndarray, sample_rate: int=24000)`; not a file writer `[CITED: kokoro-onnx examples/save.py]` |

`kokoro-onnx==0.5.0` transitively pulls `onnxruntime>=1.20.1`, `numpy>=2.0.2`, `phonemizer-fork>=3.3.2`,
`espeakng-loader>=0.2.4` `[VERIFIED: PyPI JSON install_requires]`. Python `>=3.10,<3.14` — host is
**3.13.3, in range** `[VERIFIED: python --version]`.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `kokoro-onnx` | `kokoro==0.7.16` (official, hexgrad) | Requires PyTorch + `misaki` G2P — heavier download, torch on Windows CPU. D-03 explicitly leans ONNX; reject unless GPU/PyTorch already present. |
| `soundfile` | `scipy.io.wavfile` | scipy also fine, but needs int16 conversion of the float array; `soundfile` handles float32 directly and is lighter. |

**Installation (for `install_instructions`):**
```bash
pip install "kokoro-onnx==0.5.0" soundfile
# One-time model download into ~/.kokoro (offline thereafter):
#   kokoro-v1.0.onnx  -> https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
#   voices-v1.0.bin   -> https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

**Model / voice facts** `[VERIFIED: HF hexgrad/Kokoro-82M + kokoro-onnx README]`:
- Model id: **Kokoro-82M** (82M params), files `kokoro-v1.0.onnx` (~310 MB) + `voices-v1.0.bin` (~27 MB).
- License: **Apache-2.0** — free for commercial use. Confirmed.
- Inventory: **54 voices, 8 languages** (matches TTS-01 target exactly).
- Default / flagship voice: **`af_heart`** (American English female).
- Voice-prefix → language map (lang code passed to `create(..., lang=)`):

| Prefix | Language | espeak `lang` |
|--------|----------|---------------|
| `af_`/`am_` | American English | `en-us` |
| `bf_`/`bm_` | British English | `en-gb` |
| `ef_`/`em_` | Spanish | `es` |
| `ff_` | French | `fr-fr` |
| `hf_`/`hm_` | Hindi | `hi` |
| `if_`/`im_` | Italian | `it` |
| `jf_`/`jm_` | Japanese | `ja` |
| `pf_`/`pm_` | Brazilian Portuguese | `pt-br` |
| `zf_`/`zm_` | Mandarin Chinese | `cmn` |

> Note: 9 prefix codes but **8 languages** because American+British English share one language. `[ASSUMED A2]` on the exact espeak lang strings per prefix — verify against `voices-v1.0.bin`/VOICES.md at implementation; the `lang` arg is espeak-style, wrong string only degrades phonemization for non-English.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `kokoro-onnx` | PyPI | 21 releases, latest 0.5.0 (2026-01-30) | high (widely used ONNX Kokoro fork) | github.com/thewh1teagle/kokoro-onnx | OK | Approved |
| `soundfile` | PyPI | mature/ubiquitous | very high | github.com/bastibe/python-soundfile | OK | Approved |
| `onnxruntime` | PyPI | Microsoft, ubiquitous | very high | github.com/microsoft/onnxruntime | OK | Approved (transitive) |

**Removed [SLOP]:** none. **Flagged [SUS]:** none. Package name `kokoro-onnx` was discovered via
WebSearch then verified against PyPI JSON, the GitHub source repo, and `pip index versions` (21 real
releases) — treat as `[VERIFIED]`. Do not confuse with `pykokoro` (a different holgern wrapper) or
the official `kokoro` (PyTorch).

## Architecture Patterns

### Data flow
```
inputs{text, voice, speed, lang, output_path}
   -> KokoroTTS.execute()
        -> get_status()  [import kokoro_onnx OK  AND  model files present in ~/.kokoro]
        -> Kokoro(onnx_path, voices_path)            (lazy singleton; load once)
        -> samples, sr = kokoro.create(text, voice, speed, lang)   (CPU ONNX, offline)
        -> soundfile.write(output_path, samples, sr)   sr = 24000
   -> ToolResult{success, data{provider,voice,output,format:"wav"}, artifacts:[output_path]}
```

### Minimal engine call `[CITED: kokoro-onnx examples/save.py]`
```python
from kokoro_onnx import Kokoro
import soundfile as sf

kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")   # load once
samples, sample_rate = kokoro.create(
    "Offline narration test.", voice="af_heart", speed=1.0, lang="en-us"
)                                                         # sample_rate == 24000
sf.write("out.wav", samples, sample_rate)
```

### Exact `kokoro_tts.py` BaseTool field values

Mirror `piper_tts.py`; the table calls out every field that must DIFFER from Piper.

| Field | Value | Same as Piper? |
|-------|-------|----------------|
| `name` | `"kokoro_tts"` | differs |
| `version` | `"0.1.0"` | same |
| `tier` | `ToolTier.VOICE` | same |
| `capability` | `"tts"` | same |
| `provider` | `"kokoro"` | differs |
| `stability` | `ToolStability.EXPERIMENTAL` | same (D-01) |
| `execution_mode` | `ExecutionMode.SYNC` | same |
| `determinism` | `Determinism.DETERMINISTIC` | same |
| `runtime` | `ToolRuntime.LOCAL` | same |
| `dependencies` | `["python:kokoro_onnx"]` | **DIFFERS** — Piper uses `["cmd:piper"]`; Kokoro is an importable pkg, use the `python:` prefix `check_dependencies` supports (base_tool.py L224) |
| `install_instructions` | pip line + two model-file download URLs (see Installation above) | differs |
| `agent_skills` | `["kokoro", "text-to-speech"]` | **DIFFERS** — add `"kokoro"` (author the skill; see below) |
| `capabilities` | `["text_to_speech", "offline_generation", "multilingual_generation"]` | +multilingual |
| `supports` | `{"voice_cloning": False, "multilingual": True, "offline": True, "native_audio": True}` | **DIFFERS** — `multilingual: True` (Piper False) per D-02 |
| `best_for` | `["free offline multilingual narration", "expressive local-only voiceover", "54-voice / 8-language narration"]` | differs (D-02) |
| `not_good_for` | `["voice clone matching", "real-time streaming synthesis"]` | differs |
| `input_schema` | see below (mirrors Piper shape) | differs |
| `resource_profile` | `ResourceProfile(cpu_cores=2, ram_mb=1024, vram_mb=0, disk_mb=400, network_required=False)` | ram/disk higher (ONNX model ~310 MB) |
| `retry_policy` | `RetryPolicy(max_retries=1, retryable_errors=[])` | same |
| `idempotency_key_fields` | `["text", "voice", "speed", "lang"]` | analog |
| `side_effects` | `["writes audio file to output_path"]` | same |
| `user_visible_verification` | `["Listen to generated audio for intelligibility"]` | same |
| `quality_score` | **`0.7`** | **NEW FIELD (not on Piper)** — the precedence lever, see D-05 below |
| `estimate_cost` | returns `0.0` | same (TTS-02 cost=0) |

`input_schema` (mirror Piper so the selector's pass-through call site needs no special-casing):
```python
input_schema = {
    "type": "object",
    "required": ["text"],
    "properties": {
        "text": {"type": "string"},
        "voice": {"type": "string", "default": "af_heart"},   # analog of Piper "model"/"speaker_id"
        "speed": {"type": "number", "default": 1.0},           # analog of Piper "length_scale"
        "lang": {"type": "string", "default": "en-us"},
        "output_path": {"type": "string"},
    },
}
```
> Selector note: the selector passes `voice_id`/`model_id` through (tts_selector L44-51). Kokoro's
> schema uses `voice`. Have `execute()` read `inputs.get("voice") or inputs.get("voice_id") or "af_heart"`
> so a generic `voice_id` from the selector still lands. `[ASSUMED A3]` — confirm no other call site relies on `voice_id` only.

`get_status()` must check **both** import and model files:
```python
def get_status(self) -> ToolStatus:
    try:
        import kokoro_onnx  # noqa: F401
    except ImportError:
        return ToolStatus.UNAVAILABLE
    from pathlib import Path
    d = Path(os.environ.get("KOKORO_MODEL_DIR", Path.home() / ".kokoro"))
    if (d / "kokoro-v1.0.onnx").is_file() and (d / "voices-v1.0.bin").is_file():
        return ToolStatus.AVAILABLE
    return ToolStatus.UNAVAILABLE
```

## D-05 / D-06 — Selector precedence (the part that needs care)

**There is NO hardcoded precedence.** `TTSSelector._select_best_tool` (tts_selector.py L157-187)
calls `rank_providers` (lib/scoring.py) and picks the top-ranked **available** provider. Ordering
emerges from the weighted score: `task_fit 0.30 + output_quality 0.20 + control 0.15 + reliability
0.15 + cost_efficiency 0.10 + latency 0.05 + continuity 0.05` (scoring.py L36-45).

**Kokoro vs Piper on a free-only host** — every dimension ties EXCEPT output_quality:
- cost_efficiency: both free → 1.0 (scoring.py L264).
- latency: both `runtime=local` → 0.9 (L440).
- reliability: both `experimental` → 0.8 (L406).
- continuity: no locked providers → 0.5 tie.
- output_quality: driven by `quality_score` if set, else stability map (`experimental`→0.4, L461).
  Piper leaves `quality_score` unset → 0.40. **Set Kokoro `quality_score=0.7`** → output_quality 0.70.
  Weighted edge = `(0.70-0.40)*0.20 = +0.06` — deterministic Kokoro>Piper on the auto free path, and
  it is *explainable* ("higher measured quality"). This single field satisfies the D-05 free-tier
  ordering with **no scoring-engine edit**. Also give Kokoro richer multilingual `best_for` so
  task_fit ≥ Piper on multilingual intents.
- ElevenLabs, when its key is set, already outranks both on `output_quality`/`native_audio` for
  quality intents; when no key, its status is UNAVAILABLE and it is excluded from `tool_by_provider`
  (L173-176) — so the free path is purely Kokoro>Piper. No change needed for the ElevenLabs>free ordering.

**The real fix (no-silent-downgrade contract) — edit `_select_best_tool`, lines 178-187.**
Current bug: when `preferred_provider` is an explicit provider that is registered but UNAVAILABLE
(e.g. `"elevenlabs"` with no key, i.e. a requested paid voice), the `if preferred != "auto":` loop
(L178-181) finds no match and **falls through** to the auto loop (L183-185), silently downgrading to
a free provider — violating D-05. Fix:

```python
        if preferred != "auto":
            for score_item in rankings:
                if score_item.provider == preferred and score_item.provider in tool_by_provider:
                    return tool_by_provider[score_item.provider], score_item
            # Explicit provider requested but unavailable: do NOT fall through to a
            # free provider — surface it (D-05 no-silent-downgrade contract).
            known = {t.provider for t in candidates}
            if preferred in known:
                return None, None   # execute() surfaces "requested provider unavailable"
            # else: unknown provider name -> fall through to auto ranking below

        for score_item in rankings:   # auto path only
            if score_item.provider in tool_by_provider:
                return tool_by_provider[score_item.provider], score_item
        return None, None
```
Then improve the `execute()` error (L140-141) so a `None` from an explicit unavailable preference
returns a specific message, e.g. `f"Requested TTS provider '{preferred}' is unavailable — not
downgrading to a free voice. Set its key or choose preferred_provider='auto'."` (matches the
existing accent-safe-voice contract). Also treat a paid-voice-shaped `voice_id` with
`preferred_provider="auto"` as an explicit ElevenLabs request if that is how the accent-safe
contract already signals it — **verify the existing accent-safe-voice call path before finalizing
this heuristic** `[ASSUMED A1]`.

**D-06 documentation:** update the `TTSSelector` module docstring (tts_selector.py L1-6) to state the
ElevenLabs→Kokoro→Piper precedence + the no-downgrade rule, and add/extend the TTS bullet in
`PROJECT_CONTEXT.md`.

## agent_skills bridge (TTS-02)

The existing `.agents/skills/text-to-speech/SKILL.md` teaches **HeyGen Starfish** (`mcp__heygen__*`,
`api.heygen.com`) — it does NOT teach the kokoro-onnx engine. `piper_tts` and `elevenlabs_tts`
reference it loosely, but for an honest Layer-1→Layer-3 bridge, **author a minimal
`.agents/skills/kokoro/SKILL.md`** documenting: `pip install kokoro-onnx`, the two model-file
downloads, the `Kokoro(...).create(text, voice, speed, lang)` API, sample_rate 24000, the voice
inventory, and Apache-2.0 license. Set `agent_skills = ["kokoro", "text-to-speech"]` (keeps the
generic reference + adds the accurate engine ref). This is small (~1 page) and satisfies TTS-02
properly; reusing only `text-to-speech` would point agents at the wrong engine.

## Common Pitfalls

1. **Assuming espeak-ng must be installed on Windows.** It must NOT be hand-installed — `kokoro-onnx`
   0.5.0 pulls `espeakng-loader` which bundles the shared lib. Installing a conflicting system
   espeak-ng can shadow it. Just `pip install`; do not touch PATH.
2. **Treating `create()` output as a file.** It returns `(np.float32 array, 24000)`. Writing raw
   bytes = garbage. Use `soundfile.write(path, samples, 24000)`.
3. **Re-instantiating `Kokoro()` per call.** Model load is ~seconds; cache a module-level singleton
   keyed by model dir, like the singleton hint in the get_status snippet.
4. **`get_status()` returning AVAILABLE on import alone.** The pip package can be present with model
   files missing → first `create()` raises. Gate on both (snippet above), else the selector will
   route to Kokoro and then fail at execute.
5. **Python 3.14+.** `kokoro-onnx` caps at `<3.14`. Host is 3.13.3 (fine); pin CI/runtime accordingly.
6. **Silent downgrade regression.** Do not "simplify" the selector fix back into a single
   fall-through loop — that reintroduces the D-05 violation. Add a test.

## Environment Availability

| Dependency | Required By | Available now | Version | Fallback |
|------------|-------------|---------------|---------|----------|
| Python | everything | ✓ | 3.13.3 (in `>=3.10,<3.14`) | — |
| `kokoro-onnx` | Kokoro synthesis | ✗ (not installed) | target `0.5.0` | install step (blocking, no fallback) |
| `soundfile` | WAV write | ✗ | `>=0.12` | `scipy.io.wavfile` |
| `onnxruntime` | ONNX inference | ✗ | `>=1.20.1` (transitive) | — |
| Model files (`kokoro-v1.0.onnx`, `voices-v1.0.bin`) | inference | ✗ (need one-time download) | v1.0 | none — download required, then offline |
| Network at inference | — | not required | — | fully offline after model download |

**Blocking (install step required):** `kokoro-onnx`, `soundfile`, and the two model files. None are
in `requirements.txt` yet (verified — no matches). Planner adds a `requirements`/install task + a
first-run model-download helper (into `~/.kokoro`, override `KOKORO_MODEL_DIR`).

## Verification (proves offline free synthesis — DoD)

Direct engine (run with network disabled to prove offline):
```bash
python -c "from kokoro_onnx import Kokoro; import soundfile as sf; import os; d=os.path.expanduser('~/.kokoro'); k=Kokoro(d+'/kokoro-v1.0.onnx', d+'/voices-v1.0.bin'); s,sr=k.create('Offline Kokoro test.', voice='af_heart', speed=1.0, lang='en-us'); sf.write('kokoro_test.wav', s, sr); print('OK', sr, len(s))"
```
Through the contract (proves TTS-01/02/03 wiring):
```bash
python -c "from tools.tool_registry import registry; registry.ensure_discovered(); print('kokoro_tts' in [t.name for t in registry.get_by_capability('tts')])"
# then TTSSelector.execute({'text':'Free offline narration.','preferred_provider':'kokoro','output_path':'out.wav'})
# assert result.success and selected_provider=='kokoro' and file exists, with ELEVENLABS_API_KEY unset.
```
No-downgrade assertion: with `ELEVENLABS_API_KEY` unset, `preferred_provider='elevenlabs'` must
return `success=False` with the "unavailable — not downgrading" message (NOT a Kokoro/Piper WAV).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The accent-safe-voice contract signals "requested paid voice" via `preferred_provider` (and possibly a paid-shaped `voice_id`) | D-05 selector fix | Fix may not catch a `voice_id`-only request; verify the existing accent-safe path before finalizing the heuristic |
| A2 | espeak `lang` strings per voice prefix (e.g. `pt-br`, `cmn`, `fr-fr`) | voice map | Wrong string only degrades non-English phonemization; confirm against VOICES.md at impl |
| A3 | No call site depends on Kokoro exposing `model`/`speaker_id` keys (Piper's schema) rather than `voice`/`speed` | input_schema | Selector passes `voice_id`/`model_id` through; `execute()` should accept both — low risk |

## Sources

### Primary (HIGH)
- PyPI JSON `kokoro-onnx` — v0.5.0 (2026-01-30), `install_requires`, python `<3.14,>=3.10`.
- `pip index versions kokoro-onnx / kokoro / misaki` — real release histories.
- HF `hexgrad/Kokoro-82M` — Apache-2.0, 82M params, 54 voices / 8 languages, `af_heart`.
- github.com/thewh1teagle/kokoro-onnx README — model file names/URLs, offline confirmation, `create()` API.
- Local reads: `piper_tts.py`, `elevenlabs_tts.py`, `tts_selector.py`, `lib/scoring.py`, `base_tool.py`,
  `.agents/skills/text-to-speech/SKILL.md`, `PROJECT_CONTEXT.md`, REQUIREMENTS.md.

## Metadata
- Standard stack: HIGH (versions/deps/license all tool-verified).
- Selector precedence: HIGH (read full scoring + selector source; lever + exact lines identified).
- agent_skills bridge: HIGH (read the actual existing skill — it's HeyGen, not Kokoro).
- **Valid until:** ~2026-08-21 (fast-moving package — re-verify `kokoro-onnx` version before pinning if slipped).
