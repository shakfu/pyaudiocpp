"""Who said what: Sortformer diarization, then Moonshine ASR per speaker turn.

Writes build/out/diarize.rttm (NIST RTTM) and build/out/diarize.txt.
"""

from pathlib import Path

from _common import ASSETS, ac, clock, load, mono, output, parser, resample

p = parser(__doc__)
p.add_argument("wav", nargs="?", default=ASSETS / "resources" / "four_speaker_short.wav")
p.add_argument("--threshold", type=float, default=0.5, help="speaker activity threshold, 0-1")
args = p.parse_args()

audio = resample(mono(ac.read_wav(args.wav)), 16000)  # Sortformer rejects other rates
rate = audio.sample_rate
session_kw = {"backend": args.backend, "threads": args.threads}
with ac.Registry() as registry:
    # GPU backends fix the graph size at session creation (default 20 s of audio).
    diar_opts = {"sortformer_diar.session_len_sec": max(20.0, audio.duration + 1)}
    with load(registry, "sortformer") as model, model.session("diar", options=diar_opts, **session_kw) as s:
        turns = s.run(audio=audio, options={"speaker_threshold": args.threshold}).speaker_turns
    with load(registry, "moonshine") as model, model.session("asr", **session_kw) as s:
        texts = [s.run(audio=ac.Audio(audio.samples[t.start_sample : t.end_sample], rate)).text for t in turns]

uri = Path(args.wav).stem
rttm, lines = [], []
for t, text in zip(turns, texts):
    start, dur = t.start_sample / rate, (t.end_sample - t.start_sample) / rate
    rttm.append(f"SPEAKER {uri} 1 {start:.3f} {dur:.3f} <NA> <NA> {t.speaker_id} <NA> <NA>")
    lines.append(f"{clock(t.start_sample, rate)}  {t.speaker_id}: {text.strip()}")
print("\n".join(lines))
print(f"{len(turns)} turns, {len({t.speaker_id for t in turns})} speakers")
output("diarize.rttm").write_text("\n".join(rttm) + "\n")
output("diarize.txt").write_text("\n".join(lines) + "\n")
print(f"-> {output('diarize.txt')}")
