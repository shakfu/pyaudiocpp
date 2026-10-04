"""End-to-end tests against Silero VAD, which ships inside the audio.cpp tree."""

import array

import pytest

import pyaudiocpp as ac

from conftest import BACKEND, SILERO_DIR


def test_registry_lists_families(registry):
    families = registry.families
    assert "silero_vad" in families
    assert len(families) == len(set(families))


def test_unknown_family_is_reported(registry):
    with pytest.raises(ac.AudioCppError) as info:
        registry.load(SILERO_DIR, family="no_such_family")
    assert info.value.status == ac.Status.UNSUPPORTED_FAMILY
    assert info.value.message


def test_model_metadata(silero):
    assert silero.family == "silero_vad"
    assert isinstance(silero.description, str)
    assert silero.supports("vad", "offline")
    assert silero.supports("vad", "streaming")
    assert not silero.supports("tts")
    assert not silero.supports("nonsense")
    assert isinstance(silero.languages, list)
    for scope in ac.OptionScope:
        assert isinstance(silero.options(scope), list)


def check_segments(result, frames):
    previous_end = -1
    for seg in result.segments:
        assert 0 <= seg.start_sample <= seg.end_sample <= frames
        assert seg.start_sample >= previous_end
        assert seg.text == ""
        previous_end = seg.end_sample


def test_offline_vad(silero, speech):
    with silero.session("vad", backend=BACKEND) as session:
        assert session.family == "silero_vad"
        first = session.run(audio=speech)
        with ac.Request(audio=speech) as req:
            session.prepare(req)
            second = session.run(req)
    assert first.segments, "speech fixture produced no segments"
    check_segments(first, speech.frames)
    assert first.audio is None and first.text is None
    # A reused session must give the same answer.
    assert first.segments == second.segments


def test_run_rejects_request_and_kwargs(silero, speech):
    with silero.session("vad", backend=BACKEND) as session, ac.Request(audio=speech) as req:
        with pytest.raises(TypeError):
            session.run(req, audio=speech)


def test_modes_refuse_each_other(silero, speech):
    with silero.session("vad", "offline", backend=BACKEND) as offline:
        with pytest.raises(ac.AudioCppError) as info:
            offline.stream_start()
        assert info.value.status == ac.Status.NOT_AVAILABLE
    with silero.session("vad", "streaming", backend=BACKEND) as streaming:
        with pytest.raises(ac.AudioCppError) as info:
            streaming.run(audio=speech)
        assert info.value.status == ac.Status.NOT_AVAILABLE


def test_streaming_vad(silero, speech):
    with silero.session("vad", "streaming", backend=BACKEND) as session:
        policy = session.stream_policy()
        assert policy.input == ac.StreamInput.AUDIO_CHUNKS
        chunk = policy.preferred_chunk_samples
        assert chunk > 0

        session.stream_start()
        events = []
        samples = speech.samples
        for start in range(0, len(samples) - chunk + 1, chunk):
            block = samples[start : start + chunk]
            event = session.push(block, speech.sample_rate)
            if event is not None:
                events.append(event)
            while (queued := session.next_event()) is not None:
                events.append(queued)
        assert session.next_event() is None
        result = session.finish()

    assert events
    for event in events:
        assert isinstance(event.result, ac.Result)
        for va in event.voice_activity:
            assert isinstance(va.kind, ac.VoiceActivityKind)
    assert result.segments
    check_segments(result, speech.frames)


def test_stream_offsets_track_pushed_frames(silero):
    block = array.array("f", [0.0] * 512)
    with silero.session("vad", "streaming", backend=BACKEND) as session:
        session.stream_start()
        session.push(block, 16000)
        session.push(block, 16000)
        assert session._next_sample == 1024
        session.reset()
        assert session._next_sample == 0


def test_out_of_order_close(registry, speech):
    model = registry.load(SILERO_DIR, family="silero_vad")
    session = model.session("vad", backend=BACKEND)
    model.close()  # the C session keeps its model alive
    assert session.run(audio=speech).segments
    session.close()


def test_load_and_session_options_transport(registry, speech):
    # Silero ignores options it does not declare, so this only exercises the
    # options handles, not any option's effect.
    opts = {"unused": "1", "flag": True}
    with registry.load(SILERO_DIR, family="silero_vad", options=opts) as model:
        with model.session("vad", threads=2, options=opts, backend=BACKEND) as session:
            assert session.run(audio=speech, options=opts).segments
