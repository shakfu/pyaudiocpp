"""Locate libaudiocpp and declare the ctypes prototypes for include/audiocpp.h."""

from __future__ import annotations

import ctypes
import ctypes.util
import functools
import os
import sys
from ctypes import (
    POINTER,
    Structure,
    c_char_p,
    c_double,
    c_float,
    c_int,
    c_int64,
    c_size_t,
    c_uint32,
    c_void_p,
)
from pathlib import Path

ABI_MAJOR = 0
# audiocpp_request_set_option_array and the task-vocabulary calls need 0.2.
ABI_MIN_MINOR = 2

if sys.platform == "win32":
    _LIB_NAMES = ("audiocpp.dll",)
elif sys.platform == "darwin":
    _LIB_NAMES = ("libaudiocpp.dylib",)
else:
    _LIB_NAMES = ("libaudiocpp.so", "libaudiocpp.so.0")


class ModelConfig(Structure):
    _fields_ = [
        ("family_hint", c_char_p),
        ("config_id", c_char_p),
        ("weight_id", c_char_p),
        ("model_spec_override", c_char_p),
    ]


class BackendConfig(Structure):
    _fields_ = [
        ("backend", c_char_p),
        ("device", c_int),
        ("threads", c_int),
    ]


# Opaque handles. Distinct subclasses keep argtypes checking meaningful.
class _Opaque(Structure):
    pass


class registry_t(_Opaque):
    pass


class model_t(_Opaque):
    pass


class session_t(_Opaque):
    pass


class options_t(_Opaque):
    pass


class request_t(_Opaque):
    pass


class result_t(_Opaque):
    pass


class event_t(_Opaque):
    pass


Registry_p = POINTER(registry_t)
Model_p = POINTER(model_t)
Session_p = POINTER(session_t)
Options_p = POINTER(options_t)
Request_p = POINTER(request_t)
Result_p = POINTER(result_t)
Event_p = POINTER(event_t)

c_status = c_int
c_enum = c_int
c_float_p = POINTER(c_float)
c_char_pp = POINTER(c_char_p)
c_size_p = POINTER(c_size_t)
c_int_p = POINTER(c_int)
c_int64_p = POINTER(c_int64)

# name -> (restype, argtypes)
_PROTOTYPES: dict[str, tuple[object, list[object]]] = {
    # versioning and errors
    "audiocpp_abi_version": (c_uint32, []),
    "audiocpp_build_version": (c_char_p, []),
    "audiocpp_last_error": (c_char_p, []),
    "audiocpp_status_string": (c_char_p, [c_status]),
    # options
    "audiocpp_options_create": (Options_p, []),
    "audiocpp_options_set": (c_status, [Options_p, c_char_p, c_char_p]),
    "audiocpp_options_free": (None, [Options_p]),
    # registry
    "audiocpp_registry_create": (c_status, [c_char_p, POINTER(Registry_p)]),
    "audiocpp_registry_free": (None, [Registry_p]),
    "audiocpp_registry_family_count": (c_size_t, [Registry_p]),
    "audiocpp_registry_family": (c_status, [Registry_p, c_size_t, c_char_pp]),
    # task vocabulary
    "audiocpp_task_count": (c_size_t, []),
    "audiocpp_task_name": (c_char_p, [c_size_t]),
    "audiocpp_task_from_spec_name": (c_char_p, [c_char_p]),
    # model
    "audiocpp_model_load": (
        c_status,
        [Registry_p, c_char_p, POINTER(ModelConfig), Options_p, POINTER(Model_p)],
    ),
    "audiocpp_model_free": (None, [Model_p]),
    "audiocpp_model_family": (c_char_p, [Model_p]),
    "audiocpp_model_description": (c_char_p, [Model_p]),
    "audiocpp_model_supports": (c_int, [Model_p, c_char_p, c_char_p]),
    "audiocpp_model_supports_timestamps": (c_int, [Model_p]),
    "audiocpp_model_supports_speaker_reference": (c_int, [Model_p]),
    "audiocpp_model_supports_style_condition": (c_int, [Model_p]),
    "audiocpp_model_language_count": (c_size_t, [Model_p]),
    "audiocpp_model_language": (c_status, [Model_p, c_size_t, c_char_pp]),
    "audiocpp_model_option_count": (c_size_t, [Model_p, c_enum]),
    "audiocpp_model_option": (
        c_status,
        [Model_p, c_enum, c_size_t, c_char_pp, c_char_pp, c_char_pp, c_char_pp, c_char_pp, c_char_pp, c_int_p],
    ),
    # session
    "audiocpp_session_create": (
        c_status,
        [Model_p, c_char_p, c_char_p, POINTER(BackendConfig), Options_p, POINTER(Session_p)],
    ),
    "audiocpp_session_free": (None, [Session_p]),
    "audiocpp_session_family": (c_char_p, [Session_p]),
    "audiocpp_session_prepare": (c_status, [Session_p, Request_p]),
    "audiocpp_session_run": (c_status, [Session_p, Request_p, POINTER(Result_p)]),
    # request
    "audiocpp_request_create": (Request_p, []),
    "audiocpp_request_free": (None, [Request_p]),
    "audiocpp_request_set_text": (c_status, [Request_p, c_char_p, c_char_p]),
    "audiocpp_request_set_text_language": (c_status, [Request_p, c_char_p]),
    "audiocpp_request_set_audio": (c_status, [Request_p, c_void_p, c_size_t, c_int, c_int]),
    "audiocpp_request_set_voice_audio": (c_status, [Request_p, c_void_p, c_size_t, c_int, c_int]),
    "audiocpp_request_set_voice_id": (c_status, [Request_p, c_char_p]),
    "audiocpp_request_set_style_language": (c_status, [Request_p, c_char_p]),
    "audiocpp_request_set_emotion": (c_status, [Request_p, c_char_p]),
    "audiocpp_request_set_speaking_rate": (c_status, [Request_p, c_float]),
    "audiocpp_request_set_pitch_shift": (c_status, [Request_p, c_float]),
    "audiocpp_request_set_energy_scale": (c_status, [Request_p, c_float]),
    "audiocpp_request_set_style_tag": (c_status, [Request_p, c_char_p, c_char_p]),
    "audiocpp_request_add_artifact": (
        c_status,
        [Request_p, c_enum, c_char_p, c_void_p, c_size_t, c_size_p],
    ),
    "audiocpp_request_set_artifact_meta": (c_status, [Request_p, c_size_t, c_char_p, c_char_p]),
    "audiocpp_request_set_option": (c_status, [Request_p, c_char_p, c_char_p]),
    "audiocpp_request_set_option_array": (c_status, [Request_p, c_char_p, c_char_pp, c_size_t]),
    # result
    "audiocpp_result_free": (None, [Result_p]),
    "audiocpp_result_audio": (
        c_status,
        [Result_p, POINTER(c_float_p), c_size_p, c_int_p, c_int_p],
    ),
    "audiocpp_result_text": (c_status, [Result_p, c_char_pp, c_char_pp]),
    "audiocpp_result_segment_count": (c_size_t, [Result_p]),
    "audiocpp_result_segment": (
        c_status,
        [Result_p, c_size_t, c_int64_p, c_int64_p, c_float_p, c_char_pp],
    ),
    "audiocpp_result_speaker_turn_count": (c_size_t, [Result_p]),
    "audiocpp_result_speaker_turn": (
        c_status,
        [Result_p, c_size_t, c_int64_p, c_int64_p, c_char_pp, c_float_p, c_char_pp],
    ),
    "audiocpp_result_word_count": (c_size_t, [Result_p]),
    "audiocpp_result_word": (
        c_status,
        [Result_p, c_size_t, c_char_pp, c_int64_p, c_int64_p, c_float_p],
    ),
    "audiocpp_result_named_audio_count": (c_size_t, [Result_p]),
    "audiocpp_result_named_audio": (
        c_status,
        [Result_p, c_size_t, c_char_pp, POINTER(c_float_p), c_size_p, c_int_p, c_int_p],
    ),
    "audiocpp_result_artifact_count": (c_size_t, [Result_p]),
    "audiocpp_result_artifact": (
        c_status,
        [Result_p, c_size_t, c_int_p, c_char_pp, POINTER(c_void_p), c_size_p],
    ),
    "audiocpp_result_artifact_meta_count": (c_size_t, [Result_p, c_size_t]),
    "audiocpp_result_artifact_meta": (
        c_status,
        [Result_p, c_size_t, c_size_t, c_char_pp, c_char_pp],
    ),
    # streaming
    "audiocpp_stream_policy": (
        c_status,
        [Session_p, c_int_p, c_int_p, c_int64_p, POINTER(c_double)],
    ),
    "audiocpp_stream_start": (c_status, [Session_p, Request_p]),
    "audiocpp_stream_push": (
        c_status,
        [Session_p, c_void_p, c_size_t, c_int, c_int, c_int64, POINTER(Event_p)],
    ),
    "audiocpp_stream_next_event": (c_status, [Session_p, POINTER(Event_p)]),
    "audiocpp_stream_finish": (c_status, [Session_p, POINTER(Result_p)]),
    "audiocpp_stream_reset": (c_status, [Session_p]),
    "audiocpp_event_free": (None, [Event_p]),
    "audiocpp_event_is_final": (c_int, [Event_p]),
    "audiocpp_event_as_result": (Result_p, [Event_p]),
    "audiocpp_event_voice_activity_count": (c_size_t, [Event_p]),
    "audiocpp_event_voice_activity": (
        c_status,
        [Event_p, c_size_t, c_int_p, c_int64_p, c_float_p],
    ),
}


def _candidates() -> list[str]:
    env = os.environ.get("AUDIOCPP_LIBRARY")
    if env:
        return [env]
    here = Path(__file__).resolve().parent
    found = [str(here / name) for name in _LIB_NAMES if (here / name).exists()]
    system = ctypes.util.find_library("audiocpp")
    if system:
        found.append(system)
    return found


@functools.cache
def lib() -> ctypes.CDLL:
    """Load libaudiocpp once, bind prototypes, and check the ABI version.

    Search order: $AUDIOCPP_LIBRARY, the package directory, the system loader.
    """
    candidates = _candidates()
    if not candidates:
        raise OSError(
            "libaudiocpp not found; run `make lib`, set AUDIOCPP_LIBRARY, or install a pyaudiocpp wheel"
        )
    errors = []
    for path in candidates:
        try:
            handle = ctypes.CDLL(path)
            break
        except OSError as exc:
            errors.append(f"{path}: {exc}")
    else:
        raise OSError("cannot load libaudiocpp:\n  " + "\n  ".join(errors))

    for name, (restype, argtypes) in _PROTOTYPES.items():
        fn = getattr(handle, name)
        fn.restype = restype
        fn.argtypes = argtypes

    packed = handle.audiocpp_abi_version()
    major, minor = packed >> 16, (packed >> 8) & 0xFF
    if major != ABI_MAJOR or minor < ABI_MIN_MINOR:
        raise OSError(
            f"libaudiocpp ABI {major}.{minor} is incompatible; "
            f"pyaudiocpp needs {ABI_MAJOR}.{ABI_MIN_MINOR}+ within major {ABI_MAJOR}"
        )
    return handle
