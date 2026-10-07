# Benchmarks

- Date: 2026-10-07
- Host: Apple M1, 8 cores, Darwin 25.6.0
- libaudiocpp: dev, ABI 0.2.0
- Steady = median of 3 runs after the first
- Input: `sample_16k.wav` (14.1 s); HTDemucs gets its first 4 s at 44.1 kHz; Kokoro speaks "The quick brown fox jumps over the lazy dog."
- RTF (real-time factor) = steady / audio seconds; below 1 is faster than real time

| Model | Backend | Threads | Load (s) | Session (s) | First run (s) | Steady (s) | RTF |
|-|-|-|-|-|-|-|-|
| Kokoro-82M (tts) | cpu | 1 | 4.94 | 0.45 | 6.41 | 6.57 | 2.036 |
| Kokoro-82M (tts) | cpu | 2 | 4.84 | 0.15 | 3.69 | 3.81 | 1.182 |
| Kokoro-82M (tts) | cpu | 4 | 4.59 | 0.13 | 2.21 | 2.40 | 0.744 |
| Kokoro-82M (tts) | cpu | 8 | 4.66 | 0.14 | 15.33 | 15.81 | 4.903 |
| Citrinet (asr) | cpu | 1 | 0.91 | 0.06 | 0.44 | 0.45 | 0.032 |
| Citrinet (asr) | cpu | 2 | 0.76 | 0.01 | 0.32 | 0.31 | 0.022 |
| Citrinet (asr) | cpu | 4 | 0.77 | 0.01 | 0.26 | 0.27 | 0.019 |
| Citrinet (asr) | cpu | 8 | 0.81 | 0.01 | 1.36 | 1.29 | 0.092 |
| Moonshine tiny (asr) | cpu | 1 | 2.76 | 0.01 | 0.21 | 0.21 | 0.015 |
| Moonshine tiny (asr) | cpu | 2 | 2.55 | 0.01 | 0.13 | 0.14 | 0.010 |
| Moonshine tiny (asr) | cpu | 4 | 2.56 | 0.01 | 0.09 | 0.10 | 0.007 |
| Moonshine tiny (asr) | cpu | 8 | 2.56 | 0.01 | 6.87 | 7.19 | 0.511 |
| Moonshine tiny (asr, streaming) | cpu | 1 | 2.69 | 0.01 | 0.21 | 0.21 | 0.015 |
| Moonshine tiny (asr, streaming) | cpu | 2 | 2.55 | 0.01 | 0.13 | 0.14 | 0.010 |
| Moonshine tiny (asr, streaming) | cpu | 4 | 2.57 | 0.01 | 0.10 | 0.11 | 0.008 |
| Moonshine tiny (asr, streaming) | cpu | 8 | 2.58 | 0.01 | 7.16 | 7.72 | 0.549 |
| Sortformer 4spk (diar) | cpu | 1 | 1.49 | 0.09 | 1.11 | 0.97 | 0.069 |
| Sortformer 4spk (diar) | cpu | 2 | 1.35 | 0.08 | 0.74 | 0.67 | 0.048 |
| Sortformer 4spk (diar) | cpu | 4 | 1.35 | 0.08 | 0.50 | 0.48 | 0.034 |
| Sortformer 4spk (diar) | cpu | 8 | 1.38 | 0.08 | 3.40 | 3.13 | 0.222 |
| HTDemucs (sep) | cpu | 1 | 0.04 | 0.16 | 10.61 | 10.06 | 2.516 |
| HTDemucs (sep) | cpu | 2 | 0.04 | 0.07 | 6.55 | 6.50 | 1.626 |
| HTDemucs (sep) | cpu | 4 | 0.04 | 0.08 | 4.27 | 4.32 | 1.081 |
| HTDemucs (sep) | cpu | 8 | 0.04 | 0.06 | 7.92 | 8.03 | 2.007 |
| Silero (vad) | cpu | 1 | 0.00 | 0.00 | 0.06 | 0.05 | 0.003 |
| Silero (vad) | cpu | 2 | 0.00 | 0.00 | 0.03 | 0.03 | 0.002 |
| Silero (vad) | cpu | 4 | 0.00 | 0.00 | 0.03 | 0.02 | 0.002 |
| Silero (vad) | cpu | 8 | 0.00 | 0.00 | 22.61 | 19.88 | 1.413 |
