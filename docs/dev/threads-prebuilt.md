# Benchmarks

- Date: 2026-10-07
- Host: Apple M1, 8 cores, Darwin 25.6.0
- libaudiocpp: 0.9.1-lib-test-2, ABI 0.2.0
- Steady = median of 3 runs after the first
- Input: `sample_16k.wav` (14.1 s); HTDemucs gets its first 4 s at 44.1 kHz; Kokoro speaks "The quick brown fox jumps over the lazy dog."
- RTF (real-time factor) = steady / audio seconds; below 1 is faster than real time

| Model | Backend | Threads | Load (s) | Session (s) | First run (s) | Steady (s) | RTF |
|-|-|-|-|-|-|-|-|
| Kokoro-82M (tts) | cpu | 1 | 4.75 | 0.52 | 5.92 | 5.95 | 1.845 |
| Kokoro-82M (tts) | cpu | 2 | 4.62 | 0.13 | 3.31 | 3.48 | 1.078 |
| Kokoro-82M (tts) | cpu | 4 | 4.68 | 0.13 | 2.08 | 2.14 | 0.664 |
| Kokoro-82M (tts) | cpu | 8 | 4.69 | 0.14 | 14.34 | 15.56 | 4.825 |
| Citrinet (asr) | cpu | 1 | 0.90 | 0.07 | 0.36 | 0.36 | 0.026 |
| Citrinet (asr) | cpu | 2 | 0.85 | 0.01 | 0.21 | 0.22 | 0.016 |
| Citrinet (asr) | cpu | 4 | 0.86 | 0.01 | 0.16 | 0.17 | 0.012 |
| Citrinet (asr) | cpu | 8 | 0.85 | 0.01 | 2.14 | 2.01 | 0.143 |
| Moonshine tiny (asr) | cpu | 1 | 2.90 | 0.09 | 0.43 | 0.74 | 0.052 |
| Moonshine tiny (asr) | cpu | 2 | 11.24 | 0.02 | 0.83 | 1.27 | 0.090 |
| Moonshine tiny (asr) | cpu | 4 | 10.24 | 0.02 | 1.06 | 0.68 | 0.048 |
| Moonshine tiny (asr) | cpu | 8 | 6.82 | 0.01 | 33.40 | 12.27 | 0.872 |
| Moonshine tiny (asr, streaming) | cpu | 1 | 2.96 | 0.01 | 0.37 | 0.36 | 0.026 |
| Moonshine tiny (asr, streaming) | cpu | 2 | 3.00 | 0.01 | 0.23 | 0.23 | 0.017 |
| Moonshine tiny (asr, streaming) | cpu | 4 | 2.95 | 0.01 | 0.18 | 0.19 | 0.014 |
| Moonshine tiny (asr, streaming) | cpu | 8 | 2.95 | 0.01 | 12.91 | 9.99 | 0.710 |
| Sortformer 4spk (diar) | cpu | 1 | 1.46 | 0.36 | 0.98 | 0.86 | 0.061 |
| Sortformer 4spk (diar) | cpu | 2 | 1.53 | 0.09 | 0.61 | 0.54 | 0.039 |
| Sortformer 4spk (diar) | cpu | 4 | 1.53 | 0.09 | 0.44 | 0.37 | 0.026 |
| Sortformer 4spk (diar) | cpu | 8 | 1.52 | 0.09 | 4.23 | 3.43 | 0.243 |
| HTDemucs (sep) | cpu | 1 | 0.03 | 0.15 | 11.84 | 11.77 | 2.941 |
| HTDemucs (sep) | cpu | 2 | 0.03 | 0.05 | 7.20 | 7.23 | 1.808 |
| HTDemucs (sep) | cpu | 4 | 0.03 | 0.05 | 4.93 | 5.16 | 1.289 |
| HTDemucs (sep) | cpu | 8 | 0.03 | 0.05 | 9.36 | 9.13 | 2.283 |
| Silero (vad) | cpu | 1 | 0.00 | 0.00 | 0.03 | 0.03 | 0.002 |
| Silero (vad) | cpu | 2 | 0.00 | 0.00 | 0.03 | 0.03 | 0.002 |
| Silero (vad) | cpu | 4 | 0.00 | 0.00 | 0.05 | 0.05 | 0.004 |
| Silero (vad) | cpu | 8 | 0.00 | 0.00 | 20.97 | 19.98 | 1.420 |
