import os
from pathlib import Path

import pytest

import pyaudiocpp as ac

AUDIOCPP_DIR = Path(__file__).resolve().parents[1] / "thirdparty" / "audio.cpp"
HEADER = AUDIOCPP_DIR / "include" / "audiocpp.h"
SILERO_DIR = AUDIOCPP_DIR / "assets" / "framework" / "models" / "silero_vad"
# Run every session on another backend, e.g. AUDIOCPP_TEST_BACKEND=cuda.
BACKEND = os.environ.get("AUDIOCPP_TEST_BACKEND", "cpu")
SAMPLE_WAV = AUDIOCPP_DIR / "assets" / "resources" / "sample_16k.wav"


@pytest.fixture(scope="session")
def registry():
    with ac.Registry() as reg:
        yield reg


@pytest.fixture(scope="session")
def silero(registry):
    with registry.load(SILERO_DIR, family="silero_vad") as model:
        yield model


@pytest.fixture(scope="session")
def speech():
    return ac.read_wav(SAMPLE_WAV)
