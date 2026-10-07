"""Speak text with Kokoro-82M and print per-word timings (as phonemes).

Writes build/out/tts.wav. Requires the eSpeak-ng shared library.
"""

from _common import ac, clock, load, output, parser

p = parser(__doc__)
p.add_argument("text", nargs="?", default="audio.cpp runs a hundred audio models on one runtime, from Python, with no dependencies.")
p.add_argument("--voice", default="af_heart")
p.add_argument("--language", default="en-us")
p.add_argument("--speed", type=float, default=1.0)
p.add_argument("--seed", type=int, default=1)
args = p.parse_args()

with ac.Registry() as registry, load(registry, "kokoro") as model:
    with model.session("tts", backend=args.backend, threads=args.threads) as s:
        result = s.run(
            text=args.text,
            language=args.language,
            voice_id=args.voice,
            speaking_rate=args.speed,
            options={"seed": args.seed, "return_timestamps": True},
        )

audio = result.audio
for w in result.words:
    print(f"{clock(w.start_sample, audio.sample_rate)}  {w.word}")
path = output("tts.wav")
ac.write_wav(path, audio)
print(f"{audio.duration:.2f} s at {audio.sample_rate} Hz -> {path}")
