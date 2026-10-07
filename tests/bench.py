"""Time each test model per backend; print a Markdown report.

Usage: python tests/bench.py [--backend cpu --backend metal] [--threads 4] [--runs 3]
"""

import argparse
import datetime
import os
import platform
import statistics
import subprocess
import time

import pyaudiocpp as ac

from conftest import SAMPLE_WAV, SILERO_DIR
from test_models import CITRINET, HTDEMUCS, KOKORO, MOONSHINE, PANGRAM, SORTFORMER, THREADS, linear_resample


def _stream(session, speech):
    chunk = session.stream_policy().preferred_chunk_samples
    session.stream_start()
    for i in range(0, len(speech.samples), chunk):
        session.push(speech.samples[i : i + chunk], speech.sample_rate)
        while session.next_event() is not None:
            pass
    return session.finish()


def cases(speech):
    clip = linear_resample(ac.Audio(speech.samples[: 4 * 16000], 16000), 44100)
    tts = dict(text=PANGRAM, language="en-us", voice_id="af_heart", options={"seed": 1})
    # (label, path, load kwargs, task, mode, run(session) -> Result, seconds of audio processed or None for output)
    return [
        ("Kokoro-82M (tts)", KOKORO, {"family": "kokoro_tts"}, "tts", "offline", lambda s: s.run(**tts), None),
        ("Citrinet (asr)", CITRINET, {}, "asr", "offline", lambda s: s.run(audio=speech), speech.duration),
        ("Moonshine tiny (asr)", MOONSHINE, {}, "asr", "offline", lambda s: s.run(audio=speech), speech.duration),
        ("Moonshine tiny (asr, streaming)", MOONSHINE, {}, "asr", "streaming", lambda s: _stream(s, speech), speech.duration),
        ("Sortformer 4spk (diar)", SORTFORMER, {}, "diar", "offline", lambda s: s.run(audio=speech), speech.duration),
        ("HTDemucs (sep)", HTDEMUCS, {}, "sep", "offline", lambda s: s.run(audio=clip), clip.duration),
        ("Silero (vad)", SILERO_DIR, {"family": "silero_vad"}, "vad", "offline", lambda s: s.run(audio=speech), speech.duration),
    ]


def timed(fn):
    t = time.perf_counter()
    out = fn()
    return time.perf_counter() - t, out


def bench(registry, case, backend, threads, runs):
    label, path, kw, task, mode, run, seconds = case
    if not path.exists():
        return f"| {label} | {backend} | {threads} | model not downloaded |||||"
    try:
        load, model = timed(lambda: registry.load(path, **kw))
        with model:
            init, session = timed(lambda: model.session(task, mode, threads=threads, backend=backend))
            with session:
                first, result = timed(lambda: run(session))
                steady = statistics.median(timed(lambda: run(session))[0] for _ in range(runs))
    except ac.AudioCppError as e:
        return f"| {label} | {backend} | {threads} | error: {e.message} |||||"
    seconds = seconds or result.audio.duration
    return f"| {label} | {backend} | {threads} | {load:.2f} | {init:.2f} | {first:.2f} | {steady:.2f} | {steady / seconds:.3f} |"


def host():
    if platform.system() == "Darwin":
        cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    else:
        cpu = platform.processor() or platform.machine()
    return f"{cpu}, {os.cpu_count()} cores, {platform.system()} {platform.release()}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--backend", action="append", help="repeatable; default: cpu and metal")
    p.add_argument("--threads", type=int, action="append", help=f"repeatable; default: {THREADS}")
    p.add_argument("--runs", type=int, default=3)
    args = p.parse_args()
    backends = args.backend or ["cpu", "metal"]
    thread_counts = args.threads or [THREADS]

    speech = ac.read_wav(SAMPLE_WAV)
    print("# Benchmarks\n")
    print(f"- Date: {datetime.date.today()}")
    print(f"- Host: {host()}")
    print(f"- libaudiocpp: {ac.build_version()}, ABI {'.'.join(map(str, ac.abi_version()))}")
    print(f"- Steady = median of {args.runs} runs after the first")
    print(f"- Input: `{SAMPLE_WAV.name}` ({speech.duration:.1f} s); HTDemucs gets its first 4 s at 44.1 kHz; Kokoro speaks \"{PANGRAM}\"")
    print("- RTF (real-time factor) = steady / audio seconds; below 1 is faster than real time\n")
    print("| Model | Backend | Threads | Load (s) | Session (s) | First run (s) | Steady (s) | RTF |")
    print("|-|-|-|-|-|-|-|-|")
    with ac.Registry() as registry:
        for case in cases(speech):
            for backend in backends:
                for threads in thread_counts:
                    print(bench(registry, case, backend, threads, args.runs), flush=True)


if __name__ == "__main__":
    main()
