---
name: kokoro
description: Generate free, fully offline narration with the Kokoro-82M neural model via kokoro-onnx. Use for local-only voiceover with no paid or dead key, multilingual synthesis across 54 voices / 8 languages, or when ElevenLabs/Doubao are unavailable and a zero-cost offline fallback is needed.
---

# Kokoro (offline neural TTS)

Kokoro-82M is an 82M-parameter, Apache-2.0 neural TTS model with 54 voices across
8 languages. It runs fully offline on CPU through the `kokoro-onnx` package (ONNX
Runtime, no PyTorch). Free for commercial use; no API key, no network at inference.

In OpenMontage this engine backs `tools/audio/kokoro_tts.py` (`provider="kokoro"`,
`runtime=LOCAL`, `quality_score=0.7`). Prefer it as the free offline path over Piper.

## Install

```bash
pip install "kokoro-onnx==0.5.0" soundfile
```

Do NOT hand-install system espeak-ng. `kokoro-onnx` 0.5.0 pulls `espeakng-loader`,
which bundles the espeak-ng shared library as a wheel. A conflicting system
espeak-ng can shadow it. Just `pip install`; do not touch PATH.

## Model files (one-time download)

Two pinned `model-files-v1.0` assets download once into `~/.kokoro` (override with
`KOKORO_MODEL_DIR`); inference is offline thereafter:

- `kokoro-v1.0.onnx` (~310 MB) -> https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
- `voices-v1.0.bin` (~27 MB) -> https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

In OpenMontage: `python -m tools.audio.kokoro_model_setup` (idempotent, skip-if-present).

## Engine API

```python
from kokoro_onnx import Kokoro
import soundfile as sf

kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")   # load once (seconds); cache it
samples, sample_rate = kokoro.create(
    "Offline narration test.", voice="af_heart", speed=1.0, lang="en-us"
)                                                        # sample_rate == 24000
sf.write("out.wav", samples, sample_rate)                # create() returns floats, not a file
```

- `create()` returns `(samples: np.float32 array, sample_rate=24000)`. Persist with
  `soundfile.write(path, samples, 24000)` -- writing raw bytes yields garbage.
- Cache one `Kokoro(...)` instance per model dir; do not re-instantiate per call.
- `speed` scales rate (1.0 normal); `lang` is an espeak-style string (below).

## Voices (54 voices / 8 languages) and voice-prefix -> espeak lang map

The 2-char voice prefix determines the espeak `lang`. `kokoro_tts.execute()`
auto-derives `lang` from the prefix when the caller passes none; an explicit
`lang` always overrides. Default / flagship voice: `af_heart` (American English).

| Prefix     | Language              | espeak lang | Example voices                  |
|------------|-----------------------|-------------|---------------------------------|
| af_ / am_  | American English      | en-us       | af_heart, af_bella, am_michael  |
| bf_ / bm_  | British English       | en-gb       | bf_emma, bm_george              |
| ef_ / em_  | Spanish               | es          | ef_dora, em_alex                |
| ff_        | French                | fr-fr       | ff_siwis                        |
| hf_ / hm_  | Hindi                 | hi          | hf_alpha, hm_omega              |
| if_ / im_  | Italian               | it          | if_sara, im_nicola              |
| jf_ / jm_  | Japanese              | ja          | jf_alpha, jm_kumo               |
| pf_ / pm_  | Brazilian Portuguese  | pt-br       | pf_dora, pm_alex                |
| zf_ / zm_  | Mandarin Chinese      | cmn         | zf_xiaobei, zm_yunxi            |

17 prefixes -> 9 espeak strings -> 8 languages (American + British English are one
language, two espeak strings). Enumerate live voices with `kokoro.get_voices()`.

## OpenMontage usage

```python
from tools.audio.tts_selector import TTSSelector

result = TTSSelector().execute({
    "preferred_provider": "kokoro",
    "text": "Bonjour, ceci est un test.",
    "voice_id": "ff_siwis",          # lang auto-derived -> fr-fr
    "output_path": "projects/my-video/assets/audio/narration.wav",
})
```

Or call the provider directly:

```python
from tools.audio.kokoro_tts import KokoroTTS

result = KokoroTTS().execute({
    "text": "Offline narration.",
    "voice": "af_heart",             # omit lang -> en-us
    "output_path": "out.wav",
})
```

## License

Kokoro-82M is Apache-2.0 -- free for commercial use, no attribution constraint on
generated audio.
