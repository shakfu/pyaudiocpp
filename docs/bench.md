# Benchmarks

- Date: 2026-10-07
- Host: Apple M1, 8 cores, Darwin 25.6.0
- libaudiocpp: 0.9.1-lib-test-2, ABI 0.2.0
- Steady = median of 3 runs after the first
- Input: `sample_16k.wav` (14.1 s); HTDemucs gets its first 4 s at 44.1 kHz; Kokoro speaks "The quick brown fox jumps over the lazy dog."
- RTF (real-time factor) = steady / audio seconds; below 1 is faster than real time

| Model | Backend | Threads | Load (s) | Session (s) | First run (s) | Steady (s) | RTF |
|-|-|-|-|-|-|-|-|
| Kokoro-82M (tts) | cpu | 4 | 4.79 | 0.50 | 2.35 | 2.43 | 0.754 |
| Kokoro-82M (tts) | metal | 4 | 4.97 | 0.15 | 1.03 | 0.89 | 0.276 |
| Citrinet (asr) | cpu | 4 | 0.84 | 0.06 | 0.18 | 0.18 | 0.013 |
| Citrinet (asr) | metal | 4 | 0.83 | 0.02 | 0.14 | 0.12 | 0.009 |
| Moonshine tiny (asr) | cpu | 4 | 2.81 | 0.09 | 0.23 | 0.22 | 0.016 |
| Moonshine tiny (asr) | metal | 4 | 2.73 | 0.01 | 0.14 | 0.13 | 0.009 |
| Moonshine tiny (asr, streaming) | cpu | 4 | 2.60 | 0.01 | 0.13 | 0.14 | 0.010 |
| Moonshine tiny (asr, streaming) | metal | 4 | 2.59 | 0.01 | 0.13 | 0.13 | 0.009 |
| Sortformer 4spk (diar) | cpu | 4 | 1.34 | 0.32 | 0.34 | 0.30 | 0.021 |
| Sortformer 4spk (diar) | metal | 4 | 1.36 | 0.10 | 0.27 | 0.18 | 0.013 |
| HTDemucs (sep) | cpu | 4 | 0.04 | 0.14 | 4.31 | 4.45 | 1.113 |
| HTDemucs (sep) | metal | 4 | 0.03 | 0.04 | 2.51 | 2.57 | 0.643 |
| Silero (vad) | cpu | 4 | 0.00 | 0.00 | 0.04 | 0.04 | 0.003 |
| Silero (vad) | metal | 4 | 0.00 | 0.00 | 0.40 | 0.47 | 0.034 |
