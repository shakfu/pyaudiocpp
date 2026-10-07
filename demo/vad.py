"""Find speech with streaming Silero VAD and keep only the speech.

Writes build/out/vad_speech.wav (speech segments joined) and build/out/vad.txt.
"""

import array

from _common import ASSETS, ac, clock, load, mono, output, parser, resample

p = parser(__doc__)
p.add_argument("wav", nargs="?", default=ASSETS / "resources" / "sample_16k.wav")
args = p.parse_args()

audio = resample(mono(ac.read_wav(args.wav)), 16000)  # Silero accepts only 16 kHz
rate = audio.sample_rate
with ac.Registry() as registry, load(registry, "silero") as model:
    with model.session("vad", "streaming", backend=args.backend, threads=args.threads) as s:
        chunk = s.stream_policy().preferred_chunk_samples
        s.stream_start()
        for i in range(0, audio.frames, chunk):
            block = audio.samples[i : i + chunk]
            block.extend([0.0] * (chunk - len(block)))  # Silero takes exactly `chunk` samples
            first = s.push(block, rate)
            for event in (first, *iter(s.next_event, None)):
                for va in event.voice_activity if event else ():
                    if va.kind != ac.VoiceActivityKind.SPEECH_SEGMENT:
                        print(f"  {clock(va.sample, rate)}  {va.kind.name.lower()}")
        result = s.finish()

speech = array.array("f")
lines = []
for seg in result.segments:
    speech.extend(audio.samples[seg.start_sample : seg.end_sample])
    lines.append(f"{clock(seg.start_sample, rate)} - {clock(seg.end_sample, rate)}  p={seg.confidence:.2f}")
print("\n".join(lines))
print(f"{len(result.segments)} segments; {len(speech) / rate:.1f} of {audio.duration:.1f} s is speech")
ac.write_wav(output("vad_speech.wav"), ac.Audio(speech, rate))
output("vad.txt").write_text("\n".join(lines) + "\n")
print(f"-> {output('vad_speech.wav')}")
