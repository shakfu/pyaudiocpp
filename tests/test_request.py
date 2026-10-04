import array

import pytest

import pyaudiocpp as ac
from pyaudiocpp.core import _float_view


def test_float_view_accepts_array_and_readonly_memoryview():
    samples = array.array("f", [0.0, 0.5, -0.5, 1.0])
    _, frames = _float_view(samples, 2)
    assert frames == 2
    readonly = memoryview(samples.tobytes()).cast("f")
    assert readonly.readonly
    _, frames = _float_view(readonly, 1)
    assert frames == 4


@pytest.mark.parametrize(
    "samples, channels, exc",
    [
        (array.array("d", [0.0, 1.0]), 1, TypeError),  # float64
        (array.array("h", [0, 1]), 1, TypeError),  # int16
        (array.array("f", [0.0, 1.0, 2.0]), 2, ValueError),  # ragged channels
        (array.array("f", [0.0]), 0, ValueError),
        ([0.0, 1.0], 1, TypeError),  # no buffer protocol
    ],
)
def test_float_view_rejects(samples, channels, exc):
    with pytest.raises(exc):
        _float_view(samples, channels)


def test_float_view_rejects_non_contiguous():
    view = memoryview(array.array("f", range(8)))[::2]
    with pytest.raises(ValueError, match="contiguous"):
        _float_view(view, 1)


def test_request_needs_sample_rate_for_raw_buffers():
    with pytest.raises(ValueError, match="sample_rate"):
        ac.Request(audio=array.array("f", [0.0] * 16))


def test_request_setters_accept_everything():
    audio = ac.Audio(array.array("f", [0.0] * 320), 16000, 2)
    with ac.Request(
        text="hello",
        language="en",
        text_language="en",
        audio=audio,
        voice_audio=array.array("f", [0.0] * 160),
        voice_sample_rate=16000,
        voice_id="v1",
        style_language="en",
        emotion="happy",
        speaking_rate=1.1,
        pitch_shift=0.0,
        energy_scale=1.0,
        style_tags={"tone": "warm"},
        options={"seed": 7, "flag": True, "hotwords": ["a", "b"], "empty": []},
        artifacts=[ac.Artifact(ac.ArtifactKind.CUSTOM, "x", b"\x00\x01", {"k": "v"})],
    ) as req:
        assert not req.closed
    assert req.closed


def test_closed_handle_raises():
    req = ac.Request()
    req.close()
    req.close()  # idempotent
    with pytest.raises(ValueError, match="closed"):
        req.set_text("x")


def test_numpy_buffers():
    np = pytest.importorskip("numpy")
    stereo = np.zeros((100, 2), dtype=np.float32)
    _, frames = _float_view(stereo, 2)
    assert frames == 100
    with pytest.raises(TypeError):
        _float_view(np.zeros(4, dtype=np.float64), 1)
    with pytest.raises(ValueError):
        _float_view(stereo.T, 2)  # Fortran order


def test_wav_roundtrip(tmp_path):
    src = ac.Audio(array.array("f", [0.0, 0.25, -0.25, 0.5, -0.5, 0.99]), 8000, 2)
    path = tmp_path / "x.wav"
    ac.write_wav(path, src)
    back = ac.read_wav(path)
    assert (back.sample_rate, back.channels, back.frames) == (8000, 2, 3)
    assert all(abs(a - b) < 1e-3 for a, b in zip(src.samples, back.samples))
