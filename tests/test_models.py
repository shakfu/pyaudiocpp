"""Tests against downloaded models (`make models`). Each skips if its model is absent.

$AUDIOCPP_MODELS overrides the models directory (default: ./models).
"""

import array
import math
import os
from pathlib import Path

import pytest

import pyaudiocpp as ac

from conftest import BACKEND

MODELS = Path(os.environ.get("AUDIOCPP_MODELS", Path(__file__).resolve().parents[1] / "models"))
# Above the performance-core count, ggml CPU runs slow down 10-1000x (8 threads on an M1).
THREADS = int(os.environ.get("AUDIOCPP_TEST_THREADS", ac.core.DEFAULT_THREADS))

KOKORO = MODELS / "Kokoro-82M-GGUF" / "kokoro-82m-q8_0.gguf"
CITRINET = MODELS / "Citrinet-ASR-GGUF" / "citrinet-asr-q8_0.gguf"
MOONSHINE = MODELS / "Moonshine-Streaming-GGUF" / "moonshine-streaming-tiny-q8_0.gguf"
SORTFORMER = MODELS / "Sortformer-Diar-4spk-v1-GGUF" / "sortformer-diar-4spk-v1-q8_0.gguf"
HTDEMUCS = MODELS / "HTDemucs-GGUF" / "htdemucs-q8_0.gguf"

PANGRAM = "The quick brown fox jumps over the lazy dog."


def _model(registry, path, **kw):
    if not path.exists():
        pytest.skip(f"model not downloaded: {path.relative_to(MODELS)} (make models)")
    return registry.load(path, **kw)


@pytest.fixture(scope="module")
def kokoro(registry):
    with _model(registry, KOKORO, family="kokoro_tts") as m:
        yield m


@pytest.fixture(scope="module")
def kokoro_session(kokoro):
    with kokoro.session("tts", threads=THREADS, backend=BACKEND) as s:
        yield s


@pytest.fixture(scope="module")
def moonshine(registry):
    with _model(registry, MOONSHINE) as m:
        yield m


def words_of(text):
    return "".join(c.lower() if c.isalnum() else " " for c in text).split()


def rms(samples):
    return math.sqrt(sum(s * s for s in samples) / max(len(samples), 1))


def synth(session, text, seed=1, **kw):
    return session.run(text=text, language="en-us", voice_id="af_heart", options={"seed": seed, **kw.pop("options", {})}, **kw)


def linear_resample(audio, rate):
    """Mono linear interpolation; adequate for a test fixture, not for production."""
    n = int(audio.frames * rate / audio.sample_rate)
    step = (audio.frames - 1) / max(n - 1, 1)
    src, out = audio.samples, array.array("f", bytes(4 * n))
    for i in range(n):
        x = i * step
        j = int(x)
        nxt = src[min(j + 1, audio.frames - 1)]
        out[i] = src[j] + (nxt - src[j]) * (x - j)
    return ac.Audio(out, rate, 1)


# ---- TTS ------------------------------------------------------------------


def test_kokoro_metadata(kokoro):
    assert kokoro.family == "kokoro_tts"
    assert kokoro.supports("tts")
    assert not kokoro.supports("asr")
    assert "en-us" in kokoro.languages
    opts = {o.name: o for o in kokoro.options(ac.OptionScope.REQUEST)}
    assert opts["text_chunk_size"].min_value == "32"
    assert opts["phonemes"].value_name == "string_list"
    session_opts = [o.name for o in kokoro.options(ac.OptionScope.SESSION)]
    assert all(name.startswith("kokoro_tts.") for name in session_opts)


def test_kokoro_synthesis_is_seeded(kokoro_session):
    a = synth(kokoro_session, "Seeded synthesis.", seed=7).audio
    b = synth(kokoro_session, "Seeded synthesis.", seed=7).audio
    assert (a.sample_rate, a.channels) == (24000, 1)
    assert 0.3 < a.duration < 5.0
    assert rms(a.samples) > 0.01
    assert a.samples == b.samples


def test_kokoro_timestamps(kokoro_session):
    result = synth(kokoro_session, "Hello there.", options={"return_timestamps": True})
    assert result.words
    previous_end = 0
    for word in result.words:
        assert word.word
        assert previous_end <= word.start_sample <= word.end_sample <= result.audio.frames
        previous_end = word.start_sample


def test_kokoro_phonemes_list_option(kokoro_session):
    # string_list option: travels through audiocpp_request_set_option_array.
    result = synth(kokoro_session, "hello", options={"phonemes": ["həlˈoʊ"]})
    assert result.audio.frames > 0


def test_kokoro_rejects_unknown_option(kokoro_session):
    with pytest.raises(ac.AudioCppError) as info:
        synth(kokoro_session, "x", options={"voice-id": "af_heart"})
    assert info.value.status == ac.Status.RUNTIME
    assert "voice-id" in info.value.message


# ---- ASR ------------------------------------------------------------------


@pytest.mark.parametrize("path", [CITRINET, MOONSHINE], ids=["citrinet", "moonshine"])
def test_asr_transcribes_fixture(registry, speech, path):
    with _model(registry, path) as model, model.session("asr", threads=THREADS, backend=BACKEND) as s:
        result = s.run(audio=speech)
    assert result.audio is None
    assert "mother nature" in " ".join(words_of(result.text))


@pytest.mark.parametrize("path", [CITRINET, MOONSHINE], ids=["citrinet", "moonshine"])
def test_tts_asr_roundtrip(registry, kokoro_session, path):
    # 24 kHz TTS output into 16 kHz ASR models: the families resample internally.
    audio = synth(kokoro_session, PANGRAM).audio
    with _model(registry, path) as model, model.session("asr", threads=THREADS, backend=BACKEND) as s:
        text = s.run(audio=audio).text
    assert words_of(text) == words_of(PANGRAM)


def test_moonshine_streaming(moonshine, speech):
    assert moonshine.supports("asr", "streaming")
    with moonshine.session("asr", "streaming", threads=THREADS, backend=BACKEND) as s:
        policy = s.stream_policy()
        assert policy.input == ac.StreamInput.AUDIO_CHUNKS
        chunk = policy.preferred_chunk_samples
        s.stream_start()
        for i in range(0, len(speech.samples), chunk):
            s.push(speech.samples[i : i + chunk], speech.sample_rate)
            while s.next_event() is not None:
                pass
        result = s.finish()
    assert "mother nature" in " ".join(words_of(result.text))


# ---- Diarization ------------------------------------------------------------


def test_sortformer_diarization(registry, speech):
    with _model(registry, SORTFORMER) as model:
        threshold = {o.name: o for o in model.options()}["speaker_threshold"]
        assert (threshold.min_value, threshold.max_value) == ("0", "1")
        with model.session("diar", threads=THREADS, backend=BACKEND) as s:
            result = s.run(audio=speech, options={"speaker_threshold": 0.5})
    assert result.speaker_turns
    previous_start = 0
    for turn in result.speaker_turns:
        assert turn.speaker_id.startswith("SPEAKER_")
        assert previous_start <= turn.start_sample < turn.end_sample <= speech.frames
        previous_start = turn.start_sample


# ---- Source separation -------------------------------------------------------


def test_htdemucs_named_stems(registry, speech):
    clip = linear_resample(ac.Audio(speech.samples[: 4 * 16000], 16000), 44100)
    with _model(registry, HTDEMUCS) as model, model.session("sep", threads=THREADS, backend=BACKEND) as s:
        result = s.run(audio=clip)
        with pytest.raises(ac.AudioCppError, match="44100"):
            s.run(audio=speech)  # the C API does not resample
    assert set(result.named_audio) == {"drums", "bass", "other", "vocals"}
    for stem in result.named_audio.values():
        assert (stem.frames, stem.sample_rate, stem.channels) == (clip.frames, 44100, 1)
    stems = result.named_audio
    # Speech input: the vocal stem carries the energy. Source builds before audio.cpp
    # 6418a64 leaked speech into "other" on CPU (vocals 0.05 rms, other 0.04).
    assert rms(stems["vocals"].samples) > 3 * max(rms(stems[k].samples) for k in ("drums", "bass", "other"))
