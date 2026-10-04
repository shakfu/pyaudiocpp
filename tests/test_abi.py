import re

import pytest

import pyaudiocpp as ac
from pyaudiocpp import _lib

from conftest import HEADER


def header_functions() -> set[str]:
    text = HEADER.read_text(encoding="utf-8")
    return set(re.findall(r"AUDIOCPP_API\b[^;(]*?\b(audiocpp_\w+)\s*\(", text))


def test_every_header_function_is_bound():
    declared = header_functions()
    assert declared, "no functions parsed from the header"
    assert declared == set(_lib._PROTOTYPES)


def test_header_abi_matches_binding():
    text = HEADER.read_text(encoding="utf-8")
    major = int(re.search(r"AUDIOCPP_ABI_VERSION_MAJOR (\d+)", text).group(1))
    minor = int(re.search(r"AUDIOCPP_ABI_VERSION_MINOR (\d+)", text).group(1))
    assert major == _lib.ABI_MAJOR
    assert minor >= _lib.ABI_MIN_MINOR


def test_versions():
    major, minor, _ = ac.abi_version()
    assert major == _lib.ABI_MAJOR and minor >= _lib.ABI_MIN_MINOR
    assert isinstance(ac.build_version(), str) and ac.build_version()


def test_task_vocabulary():
    tasks = ac.tasks()
    assert {"vad", "asr", "tts", "diar"} <= set(tasks)
    assert ac.task_from_spec_name("music") == "gen"
    assert ac.task_from_spec_name("no_such_task") is None


def test_status_strings():
    assert ac.status_string(ac.Status.NOT_AVAILABLE) == "not available"
    for status in ac.Status:
        assert ac.status_string(status)


def test_enum_values_match_header():
    text = HEADER.read_text(encoding="utf-8")
    pairs = {
        "AUDIOCPP_ERR_NOT_AVAILABLE": ac.Status.NOT_AVAILABLE,
        "AUDIOCPP_OPTION_SCOPE_LOAD": ac.OptionScope.LOAD,
        "AUDIOCPP_ARTIFACT_CUSTOM": ac.ArtifactKind.CUSTOM,
        "AUDIOCPP_STREAM_INPUT_AUDIO_CHUNKS": ac.StreamInput.AUDIO_CHUNKS,
        "AUDIOCPP_STREAM_OUTPUT_PULL_EVENTS": ac.StreamOutput.PULL_EVENTS,
        "AUDIOCPP_VOICE_ACTIVITY_SPEECH_SEGMENT": ac.VoiceActivityKind.SPEECH_SEGMENT,
    }
    for name, member in pairs.items():
        value = int(re.search(rf"{name}\s*=\s*(\d+)", text).group(1))
        assert value == member, name


def test_missing_library_message(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIOCPP_LIBRARY", str(tmp_path / "nope.so"))
    _lib.lib.cache_clear()
    try:
        with pytest.raises(OSError, match="cannot load libaudiocpp"):
            _lib.lib()
    finally:
        monkeypatch.undo()
        _lib.lib.cache_clear()
    assert _lib.lib()  # restored for the remaining tests
