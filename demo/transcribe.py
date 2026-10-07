"""Transcribe a WAV file, offline or streaming.

--stream feeds Moonshine fixed-size chunks; partial text prints only if the family emits it.
Writes build/out/transcribe.txt.
"""

import time

from _common import ASSETS, ac, load, output, parser

p = parser(__doc__)
p.add_argument("wav", nargs="?", default=ASSETS / "resources" / "sample_16k.wav")
p.add_argument("--model", choices=["moonshine", "citrinet"], default="moonshine")
p.add_argument("--stream", action="store_true", help="moonshine only")
args = p.parse_args()

audio = ac.read_wav(args.wav)
mode = "streaming" if args.stream else "offline"
t0 = time.perf_counter()
with ac.Registry() as registry, load(registry, args.model) as model:
    if not model.supports("asr", mode):
        p.error(f"{args.model} does not support {mode} asr")
    with model.session("asr", mode, backend=args.backend, threads=args.threads) as s:
        if args.stream:
            policy = s.stream_policy()
            chunk = policy.preferred_chunk_samples
            print(f"stream policy: {policy.output.name.lower()}, {chunk} samples per chunk")
            s.stream_start()
            for i in range(0, len(audio.samples), chunk * audio.channels):
                first = s.push(audio.samples[i : i + chunk * audio.channels], audio.sample_rate, audio.channels)
                for event in (first, *iter(s.next_event, None)):
                    if event is not None and event.result.text:
                        print(f"  partial: {event.result.text}")
            result = s.finish()
        else:
            result = s.run(audio=audio)
elapsed = time.perf_counter() - t0

print(result.text)
print(f"{audio.duration:.1f} s of audio in {elapsed:.2f} s (including model load)")
path = output("transcribe.txt")
path.write_text(result.text + "\n")
print(f"-> {path}")
