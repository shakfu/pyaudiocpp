"""Pythonic wrapper over the audiocpp C ABI.

Results and events are copied into plain Python objects as soon as the C call
returns, then the C handle is freed. Nothing borrowed from the library outlives
the call that produced it.

Handles (Registry, Model, Session, Request) are not thread-safe individually;
separate handles may be used from separate threads. ctypes releases the GIL for
the duration of each C call.
"""

from __future__ import annotations

import array
import ctypes
import enum
from collections.abc import Iterable, Mapping, Sequence
from ctypes import byref, c_char_p, c_double, c_float, c_int, c_int64, c_size_t, c_void_p
from dataclasses import dataclass, field
from typing import Any

from . import _lib
from ._lib import lib

DEFAULT_THREADS = 4  # audiocpp_cli's --threads default


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------


class Status(enum.IntEnum):
    OK = 0
    INVALID_ARGUMENT = 1
    UNSUPPORTED_FAMILY = 2
    LOAD_FAILED = 3
    RUNTIME = 4
    OUT_OF_MEMORY = 5
    OUT_OF_RANGE = 6
    NOT_AVAILABLE = 7


class OptionScope(enum.IntEnum):
    REQUEST = 0
    SESSION = 1
    LOAD = 2


class ArtifactKind(enum.IntEnum):
    SPEAKER_EMBEDDING = 0
    STYLE_EMBEDDING = 1
    PROMPT_EMBEDDING = 2
    ACOUSTIC_TOKENS = 3
    MIDI = 4
    TRANSCRIPT_ALIGNMENT = 5
    DIARIZATION_STATE = 6
    VAD_STATE = 7
    CUSTOM = 8


class StreamInput(enum.IntEnum):
    NONE = 0
    AUDIO_CHUNKS = 1


class StreamOutput(enum.IntEnum):
    FINAL_RESULT = 0
    PULL_EVENTS = 1


class VoiceActivityKind(enum.IntEnum):
    SPEECH_START = 0
    SPEECH_END = 1
    SPEECH_SEGMENT = 2


def _as_enum(cls: type[enum.IntEnum], value: int) -> Any:
    try:
        return cls(value)
    except ValueError:  # a newer library may add members
        return value


# --------------------------------------------------------------------------
# Errors and string helpers
# --------------------------------------------------------------------------


class AudioCppError(RuntimeError):
    """A non-OK status from libaudiocpp. `status` is a Status (or raw int)."""

    def __init__(self, status: int, message: str):
        self.status = _as_enum(Status, status)
        self.message = message
        name = self.status.name if isinstance(self.status, Status) else str(status)
        super().__init__(f"{name}: {message}" if message else name)


def _check(status: int) -> None:
    if status != Status.OK:
        # last_error is per-thread and must be read before any other call.
        raise AudioCppError(status, _str(lib().audiocpp_last_error()))


def _str(value: bytes | None) -> str:
    return value.decode("utf-8", errors="replace") if value else ""


def _bytes(value: str | None) -> bytes | None:
    return None if value is None else value.encode("utf-8")


# --------------------------------------------------------------------------
# Audio buffers
# --------------------------------------------------------------------------


@dataclass
class Audio:
    """Interleaved float32 PCM. `samples` holds frames * channels values."""

    samples: array.array
    sample_rate: int
    channels: int = 1

    @property
    def frames(self) -> int:
        return len(self.samples) // self.channels

    @property
    def duration(self) -> float:
        return self.frames / self.sample_rate if self.sample_rate else 0.0


def _float_view(samples: Any, channels: int) -> tuple[Any, int]:
    """Return (ctypes buffer, frames) for a float32 C-contiguous buffer.

    Accepts array('f'), a float32 numpy array, a memoryview, or anything else
    exposing the buffer protocol with format 'f'.
    """
    if channels < 1:
        raise ValueError("channels must be >= 1")
    view = memoryview(samples)
    if view.format.lstrip("@=<") != "f" or view.itemsize != 4:
        raise TypeError(f"samples must be float32, got format {view.format!r}")
    if not view.c_contiguous:
        raise ValueError("samples must be C-contiguous")
    count = view.nbytes // 4
    if count % channels:
        raise ValueError(f"{count} samples do not divide into {channels} channels")
    raw = view.cast("B")
    buf_type = ctypes.c_char * raw.nbytes
    buf = buf_type.from_buffer_copy(raw) if raw.readonly else buf_type.from_buffer(raw)
    return buf, count // channels


def _resolve_audio(audio: Any, sample_rate: int | None, channels: int | None) -> tuple[Any, int, int, int]:
    if isinstance(audio, Audio):
        samples = audio.samples
        sample_rate = audio.sample_rate if sample_rate is None else sample_rate
        channels = audio.channels if channels is None else channels
    else:
        samples = audio
        channels = 1 if channels is None else channels
    if sample_rate is None:
        raise ValueError("sample_rate is required unless audio is an Audio")
    buf, frames = _float_view(samples, channels)
    return buf, frames, sample_rate, channels


def _copy_floats(ptr: Any, count: int) -> array.array:
    out = array.array("f")
    if count:
        out.frombytes(ctypes.string_at(ptr, count * 4))
    return out


# --------------------------------------------------------------------------
# Result types
# --------------------------------------------------------------------------


@dataclass
class Segment:
    start_sample: int
    end_sample: int
    confidence: float
    text: str


@dataclass
class SpeakerTurn:
    start_sample: int
    end_sample: int
    speaker_id: str
    confidence: float
    text: str


@dataclass
class Word:
    word: str
    start_sample: int
    end_sample: int
    confidence: float


@dataclass
class Artifact:
    """Opaque payload a family produces or consumes; feed it back via Request."""

    kind: ArtifactKind | int
    id: str
    payload: bytes
    meta: dict[str, str] = field(default_factory=dict)


@dataclass
class Result:
    audio: Audio | None = None
    text: str | None = None
    language: str | None = None
    segments: list[Segment] = field(default_factory=list)
    speaker_turns: list[SpeakerTurn] = field(default_factory=list)
    words: list[Word] = field(default_factory=list)
    named_audio: dict[str, Audio] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)


@dataclass
class VoiceActivity:
    kind: VoiceActivityKind | int
    sample: int
    probability: float


@dataclass
class Event:
    is_final: bool
    result: Result
    voice_activity: list[VoiceActivity] = field(default_factory=list)


@dataclass
class OptionInfo:
    name: str
    value_name: str
    description: str
    default: str
    min_value: str
    max_value: str
    required: bool


@dataclass
class StreamPolicy:
    input: StreamInput | int
    output: StreamOutput | int
    preferred_chunk_samples: int
    preferred_chunk_seconds: float


def _read_audio(fn: Any, *args: Any) -> tuple[int, Audio | None]:
    """Call an audio accessor; returns (status, Audio or None)."""
    ptr = ctypes.POINTER(c_float)()
    frames, rate, channels = c_size_t(), c_int(), c_int()
    status = fn(*args, byref(ptr), byref(frames), byref(rate), byref(channels))
    if status != Status.OK:
        return status, None
    n = frames.value * max(channels.value, 1)
    return status, Audio(_copy_floats(ptr, n), rate.value, channels.value)


def _read_result(res: Any) -> Result:
    L = lib()
    out = Result()

    status, audio = _read_audio(L.audiocpp_result_audio, res)
    if status not in (Status.OK, Status.NOT_AVAILABLE):
        _check(status)
    out.audio = audio

    text, language = c_char_p(), c_char_p()
    status = L.audiocpp_result_text(res, byref(text), byref(language))
    if status == Status.OK:
        out.text, out.language = _str(text.value), _str(language.value)
    elif status != Status.NOT_AVAILABLE:
        _check(status)

    for i in range(L.audiocpp_result_segment_count(res)):
        start, end, conf, txt = c_int64(), c_int64(), c_float(), c_char_p()
        _check(L.audiocpp_result_segment(res, i, byref(start), byref(end), byref(conf), byref(txt)))
        out.segments.append(Segment(start.value, end.value, conf.value, _str(txt.value)))

    for i in range(L.audiocpp_result_speaker_turn_count(res)):
        start, end, spk, conf, txt = c_int64(), c_int64(), c_char_p(), c_float(), c_char_p()
        _check(
            L.audiocpp_result_speaker_turn(
                res, i, byref(start), byref(end), byref(spk), byref(conf), byref(txt)
            )
        )
        out.speaker_turns.append(
            SpeakerTurn(start.value, end.value, _str(spk.value), conf.value, _str(txt.value))
        )

    for i in range(L.audiocpp_result_word_count(res)):
        word, start, end, conf = c_char_p(), c_int64(), c_int64(), c_float()
        _check(L.audiocpp_result_word(res, i, byref(word), byref(start), byref(end), byref(conf)))
        out.words.append(Word(_str(word.value), start.value, end.value, conf.value))

    for i in range(L.audiocpp_result_named_audio_count(res)):
        name = c_char_p()
        status, named = _read_audio(
            lambda *a: L.audiocpp_result_named_audio(res, i, byref(name), *a)
        )
        _check(status)
        out.named_audio[_str(name.value)] = named

    for i in range(L.audiocpp_result_artifact_count(res)):
        kind, aid, payload, size = c_int(), c_char_p(), c_void_p(), c_size_t()
        _check(L.audiocpp_result_artifact(res, i, byref(kind), byref(aid), byref(payload), byref(size)))
        meta = {}
        for j in range(L.audiocpp_result_artifact_meta_count(res, i)):
            key, value = c_char_p(), c_char_p()
            _check(L.audiocpp_result_artifact_meta(res, i, j, byref(key), byref(value)))
            meta[_str(key.value)] = _str(value.value)
        data = ctypes.string_at(payload, size.value) if size.value else b""
        out.artifacts.append(Artifact(_as_enum(ArtifactKind, kind.value), _str(aid.value), data, meta))

    return out


def _take_result(ptr: Any) -> Result:
    try:
        return _read_result(ptr)
    finally:
        lib().audiocpp_result_free(ptr)


def _take_event(ptr: Any) -> Event | None:
    if not ptr:
        return None
    L = lib()
    try:
        activity = []
        for i in range(L.audiocpp_event_voice_activity_count(ptr)):
            kind, sample, prob = c_int(), c_int64(), c_float()
            _check(L.audiocpp_event_voice_activity(ptr, i, byref(kind), byref(sample), byref(prob)))
            activity.append(VoiceActivity(_as_enum(VoiceActivityKind, kind.value), sample.value, prob.value))
        # The event's result view is borrowed; _read_result copies it out.
        return Event(
            is_final=bool(L.audiocpp_event_is_final(ptr)),
            result=_read_result(L.audiocpp_event_as_result(ptr)),
            voice_activity=activity,
        )
    finally:
        L.audiocpp_event_free(ptr)


# --------------------------------------------------------------------------
# Handles
# --------------------------------------------------------------------------


class _Handle:
    _free_fn: str = ""

    def __init__(self, ptr: Any):
        self._ptr = ptr

    @property
    def closed(self) -> bool:
        return not self._ptr

    def _live(self) -> Any:
        if not self._ptr:
            raise ValueError(f"{type(self).__name__} is closed")
        return self._ptr

    def close(self) -> None:
        """Free the C handle. Safe in any order: children keep parents alive."""
        ptr, self._ptr = self._ptr, None
        if ptr:
            getattr(lib(), self._free_fn)(ptr)

    def __enter__(self):
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


def _make_options(options: Mapping[str, Any] | None) -> Any:
    """Build a temporary audiocpp_options; caller frees it. None -> NULL."""
    if not options:
        return None
    L = lib()
    handle = L.audiocpp_options_create()
    if not handle:
        raise MemoryError("audiocpp_options_create failed")
    try:
        for key, value in options.items():
            _check(L.audiocpp_options_set(handle, _bytes(key), _bytes(_option_str(value))))
    except BaseException:
        L.audiocpp_options_free(handle)
        raise
    return handle


def _option_str(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class Request(_Handle):
    """A task request. Keyword arguments map onto the setter of the same name.

    `options` values that are lists or tuples go through set_option_array;
    everything else is stringified (bools as "true"/"false").
    """

    _free_fn = "audiocpp_request_free"

    def __init__(
        self,
        *,
        text: str | None = None,
        language: str | None = None,
        text_language: str | None = None,
        audio: Any = None,
        sample_rate: int | None = None,
        channels: int | None = None,
        voice_audio: Any = None,
        voice_sample_rate: int | None = None,
        voice_channels: int | None = None,
        voice_id: str | None = None,
        style_language: str | None = None,
        emotion: str | None = None,
        speaking_rate: float | None = None,
        pitch_shift: float | None = None,
        energy_scale: float | None = None,
        style_tags: Mapping[str, str] | None = None,
        options: Mapping[str, Any] | None = None,
        artifacts: Iterable[Artifact] | None = None,
    ):
        ptr = lib().audiocpp_request_create()
        if not ptr:
            raise MemoryError("audiocpp_request_create failed")
        super().__init__(ptr)
        if text is not None:
            self.set_text(text, language)
        if text_language is not None:
            self.set_text_language(text_language)
        if audio is not None:
            self.set_audio(audio, sample_rate, channels)
        if voice_audio is not None:
            self.set_voice_audio(voice_audio, voice_sample_rate, voice_channels)
        if voice_id is not None:
            self.set_voice_id(voice_id)
        if style_language is not None:
            self.set_style_language(style_language)
        if emotion is not None:
            self.set_emotion(emotion)
        if speaking_rate is not None:
            self.set_speaking_rate(speaking_rate)
        if pitch_shift is not None:
            self.set_pitch_shift(pitch_shift)
        if energy_scale is not None:
            self.set_energy_scale(energy_scale)
        for key, value in (style_tags or {}).items():
            self.set_style_tag(key, value)
        for key, value in (options or {}).items():
            self.set_option(key, value)
        for artifact in artifacts or ():
            self.add_artifact(artifact)

    def set_text(self, text: str, language: str | None = None) -> Request:
        """Set text; a non-empty language also sets options["language"]."""
        _check(lib().audiocpp_request_set_text(self._live(), _bytes(text), _bytes(language)))
        return self

    def set_text_language(self, language: str) -> Request:
        """Set the transcript language without touching options["language"]."""
        _check(lib().audiocpp_request_set_text_language(self._live(), _bytes(language)))
        return self

    def set_audio(self, audio: Any, sample_rate: int | None = None, channels: int | None = None) -> Request:
        buf, frames, rate, ch = _resolve_audio(audio, sample_rate, channels)
        _check(lib().audiocpp_request_set_audio(self._live(), buf, frames, rate, ch))
        return self

    def set_voice_audio(self, audio: Any, sample_rate: int | None = None, channels: int | None = None) -> Request:
        buf, frames, rate, ch = _resolve_audio(audio, sample_rate, channels)
        _check(lib().audiocpp_request_set_voice_audio(self._live(), buf, frames, rate, ch))
        return self

    def set_voice_id(self, voice_id: str) -> Request:
        _check(lib().audiocpp_request_set_voice_id(self._live(), _bytes(voice_id)))
        return self

    def set_style_language(self, language: str) -> Request:
        _check(lib().audiocpp_request_set_style_language(self._live(), _bytes(language)))
        return self

    def set_emotion(self, emotion: str) -> Request:
        _check(lib().audiocpp_request_set_emotion(self._live(), _bytes(emotion)))
        return self

    def set_speaking_rate(self, rate: float) -> Request:
        _check(lib().audiocpp_request_set_speaking_rate(self._live(), rate))
        return self

    def set_pitch_shift(self, shift: float) -> Request:
        _check(lib().audiocpp_request_set_pitch_shift(self._live(), shift))
        return self

    def set_energy_scale(self, scale: float) -> Request:
        _check(lib().audiocpp_request_set_energy_scale(self._live(), scale))
        return self

    def set_style_tag(self, key: str, value: str) -> Request:
        _check(lib().audiocpp_request_set_style_tag(self._live(), _bytes(key), _bytes(value)))
        return self

    def set_option(self, key: str, value: Any) -> Request:
        if isinstance(value, (list, tuple)):
            items = [_bytes(_option_str(v)) for v in value]
            arr = (c_char_p * len(items))(*items)
            _check(lib().audiocpp_request_set_option_array(self._live(), _bytes(key), arr, len(items)))
        else:
            _check(lib().audiocpp_request_set_option(self._live(), _bytes(key), _bytes(_option_str(value))))
        return self

    def add_artifact(self, artifact: Artifact) -> Request:
        L = lib()
        payload = bytes(artifact.payload)
        index = c_size_t()
        _check(
            L.audiocpp_request_add_artifact(
                self._live(), int(artifact.kind), _bytes(artifact.id), payload, len(payload), byref(index)
            )
        )
        for key, value in artifact.meta.items():
            _check(L.audiocpp_request_set_artifact_meta(self._live(), index.value, _bytes(key), _bytes(value)))
        return self


class Registry(_Handle):
    """The set of model families this build can load."""

    _free_fn = "audiocpp_registry_free"

    def __init__(self, config_path: str | None = None):
        ptr = _lib.Registry_p()
        _check(lib().audiocpp_registry_create(_bytes(config_path), byref(ptr)))
        super().__init__(ptr)

    @property
    def families(self) -> list[str]:
        L = lib()
        reg = self._live()
        names = []
        for i in range(L.audiocpp_registry_family_count(reg)):
            name = c_char_p()
            _check(L.audiocpp_registry_family(reg, i, byref(name)))
            names.append(_str(name.value))
        return names

    def load(
        self,
        model_path: str,
        *,
        family: str | None = None,
        config: str | None = None,
        weight: str | None = None,
        model_spec_override: str | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> Model:
        """Load a model. `family=None` identifies the family from the path."""
        cfg = _lib.ModelConfig(_bytes(family), _bytes(config), _bytes(weight), _bytes(model_spec_override))
        opts = _make_options(options)
        ptr = _lib.Model_p()
        try:
            _check(lib().audiocpp_model_load(self._live(), _bytes(str(model_path)), byref(cfg), opts, byref(ptr)))
        finally:
            lib().audiocpp_options_free(opts)
        return Model(ptr, self)


class Model(_Handle):
    _free_fn = "audiocpp_model_free"

    def __init__(self, ptr: Any, registry: Registry):
        super().__init__(ptr)
        self.registry = registry

    @property
    def family(self) -> str:
        return _str(lib().audiocpp_model_family(self._live()))

    @property
    def description(self) -> str:
        return _str(lib().audiocpp_model_description(self._live()))

    def supports(self, task: str, mode: str = "offline") -> bool:
        """True if the model serves `task` in `mode`. Unknown tokens read False."""
        return bool(lib().audiocpp_model_supports(self._live(), _bytes(task), _bytes(mode)))

    @property
    def supports_timestamps(self) -> bool:
        return bool(lib().audiocpp_model_supports_timestamps(self._live()))

    @property
    def supports_speaker_reference(self) -> bool:
        return bool(lib().audiocpp_model_supports_speaker_reference(self._live()))

    @property
    def supports_style_condition(self) -> bool:
        return bool(lib().audiocpp_model_supports_style_condition(self._live()))

    @property
    def languages(self) -> list[str]:
        L = lib()
        m = self._live()
        out = []
        for i in range(L.audiocpp_model_language_count(m)):
            lang = c_char_p()
            _check(L.audiocpp_model_language(m, i, byref(lang)))
            out.append(_str(lang.value))
        return out

    def options(self, scope: OptionScope = OptionScope.REQUEST) -> list[OptionInfo]:
        """Options the model declares for `scope`, with defaults and bounds."""
        L = lib()
        m = self._live()
        out = []
        for i in range(L.audiocpp_model_option_count(m, int(scope))):
            s = [c_char_p() for _ in range(6)]
            required = c_int()
            _check(L.audiocpp_model_option(m, int(scope), i, *(byref(x) for x in s), byref(required)))
            out.append(OptionInfo(*(_str(x.value) for x in s), required=bool(required.value)))
        return out

    def session(
        self,
        task: str,
        mode: str = "offline",
        *,
        backend: str = "cpu",
        device: int = 0,
        threads: int = DEFAULT_THREADS,
        options: Mapping[str, Any] | None = None,
    ) -> Session:
        """Create a session. backend: cpu, cuda, hip/rocm, vulkan, metal, best."""
        bcfg = _lib.BackendConfig(_bytes(backend), device, threads)
        opts = _make_options(options)
        ptr = _lib.Session_p()
        try:
            _check(
                lib().audiocpp_session_create(
                    self._live(), _bytes(task), _bytes(mode), byref(bcfg), opts, byref(ptr)
                )
            )
        finally:
            lib().audiocpp_options_free(opts)
        return Session(ptr, self, mode)


class Session(_Handle):
    _free_fn = "audiocpp_session_free"

    def __init__(self, ptr: Any, model: Model, mode: str):
        super().__init__(ptr)
        self.model = model
        self.mode = mode
        self._next_sample = 0

    @property
    def family(self) -> str:
        return _str(lib().audiocpp_session_family(self._live()))

    def prepare(self, request: Request) -> None:
        """Force allocation early. Optional: run() always prepares."""
        _check(lib().audiocpp_session_prepare(self._live(), request._live()))

    def run(self, request: Request | None = None, **kwargs: Any) -> Result:
        """Run an offline task. Pass a Request, or Request keyword arguments."""
        if request is not None and kwargs:
            raise TypeError("pass a Request or keyword arguments, not both")
        owned = request is None
        req = Request(**kwargs) if owned else request
        ptr = _lib.Result_p()
        try:
            _check(lib().audiocpp_session_run(self._live(), req._live(), byref(ptr)))
        finally:
            if owned:
                req.close()
        return _take_result(ptr)

    # ---- streaming ------------------------------------------------------

    def stream_policy(self) -> StreamPolicy:
        inp, outp, samples, seconds = c_int(), c_int(), c_int64(), c_double()
        _check(lib().audiocpp_stream_policy(self._live(), byref(inp), byref(outp), byref(samples), byref(seconds)))
        return StreamPolicy(
            _as_enum(StreamInput, inp.value), _as_enum(StreamOutput, outp.value), samples.value, seconds.value
        )

    def stream_start(self, request: Request | None = None) -> None:
        """Start a stream, resetting any stream already in flight."""
        _check(lib().audiocpp_stream_start(self._live(), request._live() if request else None))
        self._next_sample = 0

    def push(
        self,
        samples: Any,
        sample_rate: int | None = None,
        channels: int | None = None,
        start_sample: int | None = None,
    ) -> Event | None:
        """Feed one chunk. start_sample defaults to the end of the previous chunk."""
        buf, frames, rate, ch = _resolve_audio(samples, sample_rate, channels)
        start = self._next_sample if start_sample is None else start_sample
        ev = _lib.Event_p()
        _check(lib().audiocpp_stream_push(self._live(), buf, frames, rate, ch, start, byref(ev)))
        self._next_sample = start + frames
        return _take_event(ev)

    def next_event(self) -> Event | None:
        """Pop one queued event, or None when the queue is empty."""
        ev = _lib.Event_p()
        _check(lib().audiocpp_stream_next_event(self._live(), byref(ev)))
        return _take_event(ev)

    def finish(self) -> Result:
        ptr = _lib.Result_p()
        _check(lib().audiocpp_stream_finish(self._live(), byref(ptr)))
        return _take_result(ptr)

    def reset(self) -> None:
        _check(lib().audiocpp_stream_reset(self._live()))
        self._next_sample = 0


# --------------------------------------------------------------------------
# Module-level queries
# --------------------------------------------------------------------------


def abi_version() -> tuple[int, int, int]:
    packed = lib().audiocpp_abi_version()
    return packed >> 16, (packed >> 8) & 0xFF, packed & 0xFF


def build_version() -> str:
    return _str(lib().audiocpp_build_version())


def tasks() -> list[str]:
    """Task tokens this build accepts ("vad", "asr", "tts", ...)."""
    L = lib()
    return [_str(L.audiocpp_task_name(i)) for i in range(L.audiocpp_task_count())]


def task_from_spec_name(spec_task: str) -> str | None:
    """Map a model-spec task name ("music") to its token ("gen"), or None."""
    value = lib().audiocpp_task_from_spec_name(_bytes(spec_task))
    return None if value is None else _str(value)


def status_string(status: int) -> str:
    return _str(lib().audiocpp_status_string(int(status)))


__all__: Sequence[str] = [
    "Artifact",
    "ArtifactKind",
    "Audio",
    "AudioCppError",
    "Event",
    "Model",
    "OptionInfo",
    "OptionScope",
    "Registry",
    "Request",
    "Result",
    "Segment",
    "Session",
    "SpeakerTurn",
    "Status",
    "StreamInput",
    "StreamOutput",
    "StreamPolicy",
    "VoiceActivity",
    "VoiceActivityKind",
    "Word",
    "abi_version",
    "build_version",
    "status_string",
    "task_from_spec_name",
    "tasks",
]
