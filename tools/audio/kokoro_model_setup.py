"""One-time model-file downloader for the Kokoro (kokoro-onnx) TTS provider.

Kokoro inference is fully offline once two versioned release assets are cached
locally:

    kokoro-v1.0.onnx  (~310 MB)  - the Kokoro-82M ONNX graph
    voices-v1.0.bin   (~27 MB)   - the packed voice embeddings

Both are pulled ONCE from the pinned ``model-files-v1.0`` GitHub release of
``thewh1teagle/kokoro-onnx`` over HTTPS into ``~/.kokoro`` (override with the
``KOKORO_MODEL_DIR`` env var). The download is idempotent: any file already
present on disk is skipped. After the first successful run, no network access
is needed at inference time.

Security note: URLs are pinned to the exact versioned release tag (never a
floating "latest") and are HTTPS-only, so the downloaded binary origin is
stable and auditable (threat T-HF01-01).

Do NOT install system espeak-ng: kokoro-onnx==0.5.0 ships the phonemizer
shared library transitively via ``espeakng-loader``. A conflicting system
install can shadow the bundled one.
"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

# Pinned release tag - do NOT follow a floating "latest".
_RELEASE_BASE = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
)

# (filename, url) pairs for the two required model assets.
MODEL_FILES: dict[str, str] = {
    "kokoro-v1.0.onnx": f"{_RELEASE_BASE}/kokoro-v1.0.onnx",
    "voices-v1.0.bin": f"{_RELEASE_BASE}/voices-v1.0.bin",
}


def default_model_dir() -> Path:
    """Resolve the model cache dir from KOKORO_MODEL_DIR or default ~/.kokoro."""
    env = os.environ.get("KOKORO_MODEL_DIR")
    if env:
        return Path(env)
    return Path.home() / ".kokoro"


def _download(url: str, dest: Path) -> None:
    """Stream a single asset to dest via HTTPS, writing atomically."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as resp, open(tmp, "wb") as fh:  # noqa: S310 (pinned HTTPS URL)
        while True:
            chunk = resp.read(1 << 20)  # 1 MiB
            if not chunk:
                break
            fh.write(chunk)
    tmp.replace(dest)


def ensure_models(model_dir: str | os.PathLike[str] | None = None) -> Path:
    """Ensure both Kokoro model files exist under ``model_dir``.

    Idempotent: downloads only the files that are missing. Returns the
    resolved model directory. Files already present are left untouched.
    """
    directory = Path(model_dir) if model_dir is not None else default_model_dir()
    directory.mkdir(parents=True, exist_ok=True)

    for filename, url in MODEL_FILES.items():
        dest = directory / filename
        if dest.is_file():
            print(f"[kokoro] present: {dest}")
            continue
        print(f"[kokoro] downloading {filename} -> {dest}")
        _download(url, dest)
        print(f"[kokoro] done: {dest} ({dest.stat().st_size} bytes)")

    return directory


if __name__ == "__main__":
    d = ensure_models()
    print(f"[kokoro] model dir ready: {d}")
