# pyaudiocpp

ctypes bindings for the C ABI of [audio.cpp](https://github.com/0xShug0/audio.cpp) (`include/audiocpp.h`). audio.cpp is a ggml runtime for 100+ audio models: TTS, voice cloning, ASR, VAD, diarization, source separation, voice conversion and music generation.

- No Python dependencies. Audio is `array('f')`; any float32 buffer (numpy included) is accepted as input.

- One wheel per platform serves every Python 3 (`py3-none-<platform>`), since ctypes needs no CPython ABI.

- `libaudiocpp` links its own patched ggml statically and exports only `audiocpp_*` symbols.

## Build

```sh
make lib            # clone audio.cpp at the pinned commit, build, install into src/pyaudiocpp
make models         # ~530 MB of small models for tests/test_models.py (optional)
make test
make wheel          # scikit-build-core, same CMakeLists.txt
```

Select a GPU backend with audio.cpp's CMake options:

```sh
make lib CMAKE_ARGS=-DENGINE_ENABLE_CUDA=ON
CMAKE_ARGS=-DENGINE_ENABLE_VULKAN=ON uv build --wheel
```

The library is found in this order: `$AUDIOCPP_LIBRARY`, the package directory, the system loader. It must report ABI `0.x` with `x >= 2`.

## Usage

Models come from the [audio.cpp GGUF repo](https://huggingface.co/audio-cpp/audio.cpp-gguf).

```python
import pyaudiocpp as ac

registry = ac.Registry()

# TTS. Kokoro uses the system eSpeak-ng for G2P (grapheme-to-phoneme).
tts = registry.load("models/Kokoro-82M-GGUF/kokoro-82m-q8_0.gguf", family="kokoro_tts")
with tts.session("tts", backend="cuda") as s:
    result = s.run(text="Hello from audio.cpp.", language="en-us", voice_id="af_heart", options={"seed": 1})
ac.write_wav("hello.wav", result.audio)

# ASR. Families resample input themselves; HTDemucs does not (it requires 44.1 kHz).
asr = registry.load("models/Moonshine-Streaming-GGUF/moonshine-streaming-tiny-q8_0.gguf")
with asr.session("asr") as s:
    print(s.run(audio=result.audio).text)

# Streaming VAD (Silero ships inside the audio.cpp tree)
vad = registry.load("thirdparty/audio.cpp/assets/framework/models/silero_vad", family="silero_vad")
speech = ac.read_wav("thirdparty/audio.cpp/assets/resources/sample_16k.wav")
with vad.session("vad", "streaming") as s:
    chunk = s.stream_policy().preferred_chunk_samples
    s.stream_start()
    for i in range(0, len(speech.samples) - chunk + 1, chunk):
        event = s.push(speech.samples[i : i + chunk], speech.sample_rate)
        if event is not None and event.voice_activity:
            print(event.voice_activity)
    print(s.finish().segments)
```

Task tokens (`ac.tasks()`): `vad asr diar sep gen tts clon vc s2s align vdes spk svc midi turn`. Mode is `offline` or `streaming`.

Discover what a model accepts instead of hardcoding it:

```python
for opt in tts.options(ac.OptionScope.REQUEST):
    print(opt.name, opt.default, opt.min_value, opt.max_value, opt.required)
```

## Semantics

- `Result` and `Event` are plain dataclasses. They are copied out before the C handle is freed, so they have no lifetime constraints.

- `Registry`, `Model`, `Session` and `Request` free their handle on `close()`, on context exit, or on garbage collection. The order does not matter: a C session keeps its model alive.

- Handles are not thread-safe individually. Separate handles can be used from separate threads; ctypes releases the GIL during each C call.

- Failures raise `AudioCppError` with `.status` (a `Status`) and `.message` (from `audiocpp_last_error`).

- `options` values that are lists go through `audiocpp_request_set_option_array`; bools become `"true"`/`"false"`; everything else goes through `str()`.

- Some families ignore options they do not declare (Silero does). Check `Model.options()` rather than relying on rejection.

## Licensing

pyaudiocpp is MIT and audio.cpp is Apache-2.0. Model weights keep their original licenses, and some are non-commercial; see audio.cpp's [`docs/model_licenses.md`](https://github.com/0xShug0/audio.cpp/blob/main/docs/model_licenses.md).
