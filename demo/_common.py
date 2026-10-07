"""Paths, model lookup and CLI flags shared by the demos."""

import argparse
import array
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # run from a checkout without installing

import pyaudiocpp as ac  # noqa: E402

MODELS = Path(os.environ.get("AUDIOCPP_MODELS", ROOT / "models"))
ASSETS = ROOT / "thirdparty" / "audio.cpp" / "assets"
OUT = ROOT / "build" / "out"

# name: (path, load kwargs)
MODEL = {
    "kokoro": (MODELS / "Kokoro-82M-GGUF" / "kokoro-82m-q8_0.gguf", {"family": "kokoro_tts"}),
    "citrinet": (MODELS / "Citrinet-ASR-GGUF" / "citrinet-asr-q8_0.gguf", {}),
    "moonshine": (MODELS / "Moonshine-Streaming-GGUF" / "moonshine-streaming-tiny-q8_0.gguf", {}),
    "sortformer": (MODELS / "Sortformer-Diar-4spk-v1-GGUF" / "sortformer-diar-4spk-v1-q8_0.gguf", {}),
    "htdemucs": (MODELS / "HTDemucs-GGUF" / "htdemucs-q8_0.gguf", {}),
    "silero": (ASSETS / "framework" / "models" / "silero_vad", {"family": "silero_vad"}),
}


def parser(doc):
    p = argparse.ArgumentParser(description=doc.strip().splitlines()[0])
    p.add_argument("--backend", default="cpu", help="cpu, metal, cuda, vulkan, best (default: cpu)")
    p.add_argument("--threads", type=int, default=ac.core.DEFAULT_THREADS, help="keep at or below the performance-core count")
    return p


def load(registry, name):
    path, kw = MODEL[name]
    if not path.exists():
        sys.exit(f"{name}: {path} not found (run `make models` or `make sync`)")
    return registry.load(path, **kw)


def output(name):
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT / name


def mono(audio):
    if audio.channels == 1:
        return audio
    c, s = audio.channels, audio.samples
    return ac.Audio(array.array("f", (sum(s[i : i + c]) / c for i in range(0, len(s), c))), audio.sample_rate)


def resample(audio, rate):
    """Linear interpolation of mono audio; enough for a demo, not for production."""
    if audio.sample_rate == rate:
        return audio
    n = int(audio.frames * rate / audio.sample_rate)
    step = (audio.frames - 1) / max(n - 1, 1)
    src, out = audio.samples, array.array("f", bytes(4 * n))
    for i in range(n):
        x = i * step
        j = int(x)
        out[i] = src[j] + (src[min(j + 1, audio.frames - 1)] - src[j]) * (x - j)
    return ac.Audio(out, rate)


def clock(sample, rate):
    s = sample / rate
    return f"{int(s // 60):02d}:{s % 60:05.2f}"
