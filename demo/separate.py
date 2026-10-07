"""Split audio into drums, bass, other and vocals with HTDemucs.

HTDemucs requires 44.1 kHz and the C API does not resample, so input is
downmixed and resampled here. Writes build/out/stems/<stem>.wav.
"""

from _common import ASSETS, ac, load, mono, output, parser, resample

p = parser(__doc__)
p.add_argument("wav", nargs="?", default=ASSETS / "resources" / "sample.wav")
p.add_argument("--seconds", type=float, default=10.0, help="process only the first N seconds (0: all)")
args = p.parse_args()

audio = mono(ac.read_wav(args.wav))
if args.seconds:
    audio = ac.Audio(audio.samples[: int(args.seconds * audio.sample_rate)], audio.sample_rate)
clip = resample(audio, 44100)

with ac.Registry() as registry, load(registry, "htdemucs") as model:
    with model.session("sep", backend=args.backend, threads=args.threads) as s:
        stems = s.run(audio=clip).named_audio

output("stems").mkdir(exist_ok=True)
for name, stem in stems.items():
    rms = (sum(x * x for x in stem.samples) / max(len(stem.samples), 1)) ** 0.5
    path = output("stems") / f"{name}.wav"
    ac.write_wav(path, stem)
    print(f"{name:7} rms={rms:.4f}  -> {path}")
