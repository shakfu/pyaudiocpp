"""Minimal 16-bit PCM WAV I/O on the stdlib `wave` module."""

from __future__ import annotations

import array
import sys
import wave
from os import PathLike

from .core import Audio


def read_wav(path: str | PathLike[str]) -> Audio:
    """Read a 16-bit PCM WAV file into float32 Audio in [-1, 1)."""
    with wave.open(str(path), "rb") as f:
        if f.getsampwidth() != 2:
            raise ValueError(f"{path}: only 16-bit PCM is supported, got {8 * f.getsampwidth()}-bit")
        pcm = array.array("h", f.readframes(f.getnframes()))
        channels, rate = f.getnchannels(), f.getframerate()
    if sys.byteorder == "big":
        pcm.byteswap()
    return Audio(array.array("f", (s / 32768.0 for s in pcm)), rate, channels)


def write_wav(path: str | PathLike[str], audio: Audio) -> None:
    """Write Audio as 16-bit PCM, clipping to [-1, 1]."""
    pcm = array.array("h", (int(max(-1.0, min(1.0, s)) * 32767) for s in audio.samples))
    if sys.byteorder == "big":
        pcm.byteswap()
    with wave.open(str(path), "wb") as f:
        f.setnchannels(audio.channels)
        f.setsampwidth(2)
        f.setframerate(audio.sample_rate)
        f.writeframes(pcm.tobytes())
