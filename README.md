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

On macOS, OpenMP is off by default, as in upstream's release build. Otherwise the dylib and wheel would depend on Homebrew's `libomp`. To enable it:

```sh
make lib CMAKE_ARGS="-DENGINE_ENABLE_OPENMP=ON -DGGML_OPENMP=ON -DOpenMP_ROOT=$(brew --prefix libomp)"
```

The library is found in this order: `$AUDIOCPP_LIBRARY`, the package directory, the system loader. It must report ABI `0.x` with `x >= 2`.

### Prebuilt library

audio.cpp publishes `libaudiocpp` in its releases ([audio.cpp#779](https://github.com/0xShug0/audio.cpp/issues/779)). The 0.9.1 macOS arm64 build passes the full test suite on CPU and Metal without changes:

```sh
AUDIOCPP_LIBRARY=$PWD/thirdparty/audiocpp-0.9.1-lib/libs/libaudiocpp.dylib make test
```

- It was built from `6418a64` (branch `fix/779-release-libaudiocpp`), the commit pyaudiocpp now pins. `audiocpp.h` is unchanged since the previous pin `e3e1bc7`; ABI 0.2.0.
- Source builds at `e3e1bc7` separated HTDemucs stems wrongly on CPU: on speech, vocals fell from 0.12 to 0.05 rms and `other` rose from 0.002 to 0.04. Metal was correct. Builds at `6418a64` match the prebuilt, so the fix lies in the 31 commits between them, probably [#790](https://github.com/0xShug0/audio.cpp/pull/790). `test_htdemucs_named_stems` now catches it.
- It exports 74 `audiocpp_*` symbols, all bound by pyaudiocpp.
- It links only system frameworks and libc++; ggml is static, and OpenMP is not used. Requires macOS 13.3+.
- Its install name is `@rpath/libaudiocpp.0.dylib`, so it can go into a wheel unpatched.
- It does not bundle eSpeak-ng (see Kokoro below).
- The file is versioned `0.1.0` but reports ABI `0.2.0`. It reports build `0.9.1-lib-test-2`, but no `v0.9.1` release or tag exists; the latest release is `v0.9.0`.

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

# ASR. Moonshine and Citrinet resample input themselves; see "Tested models" for those that do not.
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

## Demos

`demo/` runs each tested model on audio from the audio.cpp tree. Outputs go to `build/out/`. Each script takes `--backend` and `--threads`; `-h` lists the rest.

| Script | Does | Writes |
|-|-|-|
| `tts.py [text]` | Kokoro speech with per-word timings | `tts.wav` |
| `transcribe.py [wav] [--model citrinet] [--stream]` | Moonshine or Citrinet ASR | `transcribe.txt` |
| `vad.py [wav]` | streaming Silero; keeps only the speech | `vad_speech.wav`, `vad.txt` |
| `diarize.py [wav]` | Sortformer speaker turns, then Moonshine per turn | `diarize.txt`, `diarize.rttm` |
| `separate.py [wav]` | HTDemucs drums, bass, other, vocals | `stems/*.wav` |

```sh
make demo                                   # all five, CPU
uv run python demo/diarize.py --backend metal
```

## Tested models

`make models` downloads the first five; Silero ships in the audio.cpp tree.

| Model | Task | Size | Requires |
|-|-|-|-|
| `kokoro-82m-q8_0` | tts | 193 MB | `family="kokoro_tts"`; eSpeak-ng shared library (`brew install espeak-ng`, `apt install libespeak-ng1`). `Word.word` holds phonemes, not the input text |
| `citrinet-asr-q8_0` | asr | 39 MB | - |
| `moonshine-streaming-tiny-q8_0` | asr, offline and streaming | 58 MB | Streaming events carry no text; it arrives from `finish()` (policy `FINAL_RESULT`) |
| `sortformer-diar-4spk-v1-q8_0` | diar, up to 4 speakers | 176 MB | 16 kHz input. On GPU backends, input longer than `sortformer_diar.session_len_sec` (default 20 s) fails with `request exceeds fixed graph capacity`; raise it at session creation |
| `htdemucs-q8_0` | sep, 4 stems | 60 MB | 44.1 kHz input; the C API does not resample it |
| `silero_vad` | vad | 1.2 MB | `family="silero_vad"`; 16 kHz input; streaming chunks of exactly 512 samples |

libaudiocpp loads eSpeak-ng at run time from `/opt/homebrew/lib`, `/usr/local/lib`, the Linux multiarch directories, then the system loader. Without it, Kokoro raises `RUNTIME: Could not load eSpeak-ng`.

### Speed

RTF (real-time factor) is processing time divided by audio duration; below 1 is faster than real time. Prebuilt 0.9.1 library, Apple M1 (4 performance + 4 efficiency cores), 4 threads, median of 3 runs. Full report, with load and first-run times: [`docs/bench.md`](docs/bench.md) (`make bench`).

| Model | CPU RTF | Metal RTF |
|-|-|-|
| Kokoro-82M | 0.75 | 0.28 |
| Citrinet | 0.013 | 0.009 |
| Moonshine tiny | 0.016 | 0.009 |
| Moonshine tiny, streaming | 0.010 | 0.009 |
| Sortformer | 0.021 | 0.013 |
| HTDemucs | 1.11 | 0.64 |
| Silero | 0.003 | 0.034 |

- Metal helps most on Kokoro (2.7x) and HTDemucs (1.7x).
- Silero is 10x slower on Metal than on CPU.
- Load time is the same on both backends: up to 4.8 s (Kokoro).

### Threads

Set `threads` to at most the number of performance cores. On the M1, Silero and Citrinet slow down from 6 threads, and every model slows down sharply at 8 (all cores). The prebuilt and both source builds (with and without OpenMP) behave the same, so neither OpenMP nor the release build is the cause. Steady-state CPU seconds:

| Threads | 4 | 5 | 6 | 7 | 8 |
|-|-|-|-|-|-|
| Silero | 0.05-0.08 | 0.09-0.18 | 0.65-2.98 | 3.70-4.84 | 20-127 |
| Citrinet | 0.24-0.46 | 0.27-0.81 | 0.47-2.07 | 1.73-5.31 | 1.3-7.7 |
| Kokoro (prebuilt) | 1.62 | 1.69 | 1.66 | 1.74 | 16-21 |

Kokoro does not slow down until 8 threads; its larger operations may hide the synchronisation cost (unverified). Moonshine takes 7-40 s at 8 threads against 0.1-0.7 s at 4. The 8-thread times vary up to 6x between runs. Per-build sweeps: [`docs/dev/`](docs/dev/) (`PYTHONPATH=src uv run python tests/bench.py --backend cpu --threads 1 --threads 8`).

`Session` defaults to 4 threads, matching `audiocpp_cli`. The C API defaults to 1 when `backend_config` is NULL; Kokoro then takes 6.0 s instead of 2.1 s.

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
