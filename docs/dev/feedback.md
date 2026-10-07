Thanks for this. I tested `audiocpp-0.9.1-lib` (macOS arm64, build `0.9.1-lib-test-2`, commit 6418a64) with pyaudiocpp, a ctypes binding for `audiocpp.h`.

It works as shipped:

- All 74 exported `audiocpp_*` symbols bind, and ABI 0.2.0 matches the header.
- Only system frameworks and libc++ are linked, and `@rpath/libaudiocpp.0.dylib` lets it go into a wheel unpatched.
- The full test suite passes on CPU and Metal. It covers Kokoro, Citrinet, Moonshine (offline and streaming), Sortformer, HTDemucs and Silero.

Some feedback, most important first:

**1. Thread count above the performance-core count makes CPU runs much slower.** On an M1 (4 performance + 4 efficiency cores), small models slow down from 6 threads, and every model slows down sharply at 8 (all cores). Steady-state seconds:

| threads | 4 | 5 | 6 | 7 | 8 |
|-|-|-|-|-|-|
| Silero VAD (14 s audio) | 0.05 | 0.09 | 0.65 | 3.7 | 20-127 |
| Citrinet (14 s audio) | 0.24 | 0.27 | 0.47 | 1.7 | 1.3-7.7 |
| Kokoro (pangram) | 1.6 | 1.7 | 1.7 | 1.7 | 16-21 |

The same happens with this release and with source builds at e3e1bc7, with and without OpenMP. At 8 threads, timings vary up to 6x between runs. Could `audiocpp_backend_config` accept something like `threads = 0` to mean "auto: performance cores"? Then every binding would get a safe default. Otherwise, a note in `audiocpp.h` would help.

**2. Versioning.** The dylib is versioned `0.1.0`, but `audiocpp_abi_version` reports 0.2.0. There is also no `v0.9.1` tag, and 6418a64 exists only on `fix/779-release-libaudiocpp`. A tag on `main` for each lib release would let bindings pin the source that matches the binary.

**3. eSpeak-ng is not bundled.** Kokoro raises `Could not load eSpeak-ng` until it is installed. Release notes for the lib package could say so.

**4. Sortformer on GPU fails for input longer than 20 s**, with `request exceeds fixed graph capacity`. Setting `sortformer_diar.session_len_sec` fixes it, but the error doesn't name that option. Naming it in the error would save users a search.

**5. Source build on macOS.** `ENGINE_ENABLE_OPENMP` defaults to ON, so configuring with Apple clang fails unless Homebrew's `libomp` is located by hand. Your release builds without OpenMP. Defaulting it to OFF on Apple would match that.

**6. FYI:** source builds at e3e1bc7 separated HTDemucs stems wrongly on CPU. On speech, vocals rms fell from 0.12 to 0.05, and the `other` stem rose from 0.002 to 0.04. Metal was correct. At 6418a64 CPU matches Metal, so it's already fixed, probably by #790.

The same run also built lib packages for Linux x64 (CPU, CPU-portable, Vulkan, CUDA 12.8/13.3), Windows x64 and macOS x64. Thanks for covering all of them.
