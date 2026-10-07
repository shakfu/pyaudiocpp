# Benchmarks

- Date: 2026-10-07
- Host: Apple M1, 8 cores, Darwin 25.6.0
- libaudiocpp: dev, ABI 0.2.0
- Steady = median of 3 runs after the first
- Input: `sample_16k.wav` (14.1 s); HTDemucs gets its first 4 s at 44.1 kHz; Kokoro speaks "The quick brown fox jumps over the lazy dog."
- RTF (real-time factor) = steady / audio seconds; below 1 is faster than real time

| Model | Backend | Threads | Load (s) | Session (s) | First run (s) | Steady (s) | RTF |
|-|-|-|-|-|-|-|-|
| Kokoro-82M (tts) | cpu | 1 | 4.68 | 0.41 | 5.87 | 5.81 | 1.802 |
| Kokoro-82M (tts) | cpu | 2 | 4.49 | 0.15 | 3.39 | 3.41 | 1.058 |
| Kokoro-82M (tts) | cpu | 4 | 4.48 | 0.13 | 2.01 | 2.90 | 0.899 |
| Kokoro-82M (tts) | cpu | 8 | 6.47 | 0.33 | 17.04 | 16.59 | 5.143 |
| Citrinet (asr) | cpu | 1 | 0.79 | 0.08 | 0.33 | 0.32 | 0.022 |
| Citrinet (asr) | cpu | 2 | 0.75 | 0.01 | 0.16 | 0.18 | 0.013 |
| Citrinet (asr) | cpu | 4 | 0.75 | 0.01 | 0.10 | 0.11 | 0.008 |
| Citrinet (asr) | cpu | 8 | 0.76 | 0.01 | 1.88 | 1.27 | 0.090 |
| Moonshine tiny (asr) | cpu | 1 | 2.64 | 0.10 | 0.21 | 0.22 | 0.015 |
| Moonshine tiny (asr) | cpu | 2 | 2.64 | 0.01 | 0.15 | 0.15 | 0.011 |
| Moonshine tiny (asr) | cpu | 4 | 3.22 | 0.01 | 0.30 | 0.23 | 0.016 |
| Moonshine tiny (asr) | cpu | 8 | 3.12 | 0.01 | 13.03 | 39.56 | 2.811 |
| Moonshine tiny (asr, streaming) | cpu | 1 | 3.19 | 0.01 | 0.27 | 0.26 | 0.019 |
| Moonshine tiny (asr, streaming) | cpu | 2 | 3.14 | 0.01 | 0.19 | 0.18 | 0.013 |
| Moonshine tiny (asr, streaming) | cpu | 4 | 3.19 | 0.01 | 0.21 | 0.23 | 0.016 |
| Moonshine tiny (asr, streaming) | cpu | 8 | 3.18 | 0.01 | 38.50 | 38.18 | 2.713 |
| Sortformer 4spk (diar) | cpu | 1 | 1.67 | 0.49 | 1.35 | 0.95 | 0.068 |
| Sortformer 4spk (diar) | cpu | 2 | 1.64 | 0.15 | 1.16 | 0.61 | 0.043 |
| Sortformer 4spk (diar) | cpu | 4 | 1.55 | 0.09 | 0.72 | 0.35 | 0.025 |
| Sortformer 4spk (diar) | cpu | 8 | 1.58 | 0.11 | 25.85 | 3.31 | 0.235 |
| HTDemucs (sep) | cpu | 1 | 0.03 | 0.15 | 10.48 | 10.09 | 2.522 |
| HTDemucs (sep) | cpu | 2 | 0.02 | 0.05 | 6.37 | 6.47 | 1.618 |
| HTDemucs (sep) | cpu | 4 | 0.02 | 0.04 | 4.47 | 4.53 | 1.133 |
| HTDemucs (sep) | cpu | 8 | 0.03 | 0.05 | 9.15 | 8.51 | 2.128 |
| Silero (vad) | cpu | 1 | 0.00 | 0.00 | 0.03 | 0.03 | 0.002 |
| Silero (vad) | cpu | 2 | 0.00 | 0.00 | 0.04 | 0.03 | 0.002 |
| Silero (vad) | cpu | 4 | 0.00 | 0.00 | 0.04 | 0.04 | 0.003 |
| Silero (vad) | cpu | 8 | 0.00 | 0.00 | 19.10 | 58.56 | 4.161 |
