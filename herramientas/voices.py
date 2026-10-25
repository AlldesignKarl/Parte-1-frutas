"""Genera todas las voces de una parte: python3 voices.py N outdir
Crea outdir/lineNN.wav (24 kHz) y outdir/lines.json con fonemas, duraciones y metadatos."""
import json
import os
import re
import subprocess
import sys

import numpy as np
import onnxruntime as ort
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gen"))
import tts  # noqa: E402

SR = 24000
# voz: mezcla Kokoro · speed · pitch (semitonos) · formantes ('p' conservados / 's' desplazados) · efecto base
CAST = {
    "NARRADOR": dict(voice="em_alex", speed=0.9, pitch=-1.5, formant="p", fx="narr"),
    "BRUNO": dict(voice="em_alex", speed=1.0, pitch=0.0, formant="p"),
    "TEO": dict(voice="em_alex", speed=1.08, pitch=1.0, formant="p"),
    "ORTEGA": dict(voice="em_santa", speed=0.95, pitch=0.0, formant="p", fx="rasp"),
    "VICENTE": dict(voice="em_santa", speed=0.88, pitch=-1.0, formant="p"),
    "ROCCO": dict(voice="em_santa", speed=0.95, pitch=-2.0, formant="p"),
    "LIA": dict(voice="ef_dora", speed=1.03, pitch=0.0, formant="p"),
    "VALERIA": dict(voice="ef_dora", speed=0.9, pitch=-1.5, formant="p"),
    "PRESENTADORA": dict(voice="ef_dora", speed=1.0, pitch=-0.5, formant="p"),
    "NICO": dict(voice="ef_dora", speed=1.08, pitch=3.0, formant="s"),
}

_sess = None


def session():
    global _sess
    if _sess is None:
        so = ort.SessionOptions()
        so.intra_op_num_threads = os.cpu_count()
        _sess = ort.InferenceSession(os.path.join(tts.M, "kokoro-v1.0-q8-dur.onnx"), so,
                                     providers=["CPUExecutionProvider"])
    return _sess


def delivery(tag_text):
    """Ajustes según las etiquetas de interpretación: [whispers], [shouting], [slow]…"""
    t = tag_text.lower()
    d = dict(speed=1.0, gain=0.0, whisper=False)
    if any(k in t for k in ("whisper", "susurr")):
        d.update(whisper=True, gain=-5.0, speed=0.97)
    if any(k in t for k in ("shout", "roar", "grit", "panick", "furious")):
        d.update(gain=2.5, speed=1.06)
    if any(k in t for k in ("urgent", "fast", "intense", "breathless", "out of breath", "anxious")):
        d["speed"] *= 1.06
    if any(k in t for k in ("slow", "ominous", "deep")):
        d["speed"] *= 0.93
    if any(k in t for k in ("shiver", "weak", "trembl", "broken")):
        d["speed"] *= 0.92
    return d


def clean_for_tts(text):
    text = text.replace("[pause]", "…")
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = text.replace("...", "…")
    return re.sub(r"\s+", " ", text).strip()


def synth_line(text, voice, speed):
    sess = session()
    pack = tts.voice_mix(voice)
    chunks = [c for c in re.split(r"(?<=[.!?…])\s+", text) if c.strip()]
    wav, phones, durs = [], [], []
    for i, c in enumerate(chunks):
        ps = tts.phonemize(c)
        ids = [tts.VOCAB[p] for p in ps][:508]
        ps = ps[:508]
        style = pack[min(len(ids), pack.shape[0] - 1)]
        w, d = sess.run(None, {
            "input_ids": np.array([[0] + ids + [0]], dtype=np.int64),
            "style": style.astype(np.float32),
            "speed": np.array([speed], dtype=np.float32),
        })
        d = d.reshape(-1)
        w = w.reshape(-1)
        # el audio dura sum(d)*600 muestras; los tokens de borde (0) son silencio
        phones += [" "] + list(ps) + [" "]
        durs += [float(x) for x in d]
        wav.append(w)
        if i < len(chunks) - 1:
            gap = 0.22
            wav.append(np.zeros(int(SR * gap), np.float32))
            phones.append(" ")
            durs.append(gap * SR / 600)
    return np.concatenate(wav), phones, durs


def post(in_wav, out_wav, pitch, formant, fx, mode, gain, whisper):
    filt = []
    if abs(pitch) > 0.01:
        ratio = 2 ** (pitch / 12)
        filt.append(f"rubberband=pitch={ratio:.5f}:formant={'preserved' if formant == 'p' else 'shifted'}"
                    ":pitchq=quality:transients=smooth")
    filt.append("highpass=f=70")
    if fx == "rasp":
        filt.append("acompressor=threshold=0.1:ratio=3,asoftclip=type=tanh:threshold=0.9")
    if whisper:
        filt.append("highpass=f=250,treble=g=3")
    if mode == "tv":
        filt.append("highpass=f=220,lowpass=f=5500,aecho=0.8:0.5:18:0.18")
    elif mode == "intercom":
        filt.append("highpass=f=350,lowpass=f=3200,acrusher=bits=10:mix=0.25,aecho=0.8:0.6:35:0.25")
    elif mode == "tel":
        filt.append("highpass=f=300,lowpass=f=3400")
    if fx == "narr":
        filt.append("bass=g=3:f=120,aecho=0.8:0.55:60|110:0.18|0.10")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", in_wav, "-af", ",".join(filt), "-ar", str(SR), out_wav],
                   check=True)
    normalize(out_wav, gain)


def normalize(path, gain_db=0.0, target_db=-19.0):
    """Iguala el volumen de todas las frases (RMS de las partes con voz) y limita picos."""
    a, sr = sf.read(path)
    frame = int(sr * 0.02)
    n = len(a) // frame
    if n == 0:
        return
    rms = np.sqrt((a[:n * frame].reshape(n, frame) ** 2).mean(1) + 1e-12)
    active = rms[rms > rms.max() * 0.1]
    level = 20 * np.log10(np.sqrt((active ** 2).mean()) + 1e-9)
    a = a * 10 ** ((target_db + gain_db - level) / 20)
    peak = np.abs(a).max()
    if peak > 0.95:
        a = np.tanh(a / peak * 1.2) / np.tanh(1.2) * 0.95
    sf.write(path, a.astype(np.float32), sr)


def build(num, outdir):
    import importlib
    P = importlib.import_module(f"part{num}").PART
    os.makedirs(outdir, exist_ok=True)
    meta = []
    n = 0
    for si, s in enumerate(P["shots"]):
        for li, (spk, text, tag, mode) in enumerate(s.get("lines", [])):
            n += 1
            c = CAST[spk]
            d = delivery(text + " " + tag)
            clean = clean_for_tts(text)
            wav, phones, durs = synth_line(clean, c["voice"], c["speed"] * d["speed"])
            raw = os.path.join(outdir, f"raw{n:02d}.wav")
            out = os.path.join(outdir, f"line{n:02d}.wav")
            sf.write(raw, wav, SR)
            post(raw, out, c["pitch"], c["formant"], c.get("fx"), mode, d["gain"], d["whisper"])
            os.remove(raw)
            dur = sf.info(out).duration
            meta.append(dict(n=n, shot=si, idx=li, speaker=spk, mode=mode, text=re.sub(r"\[[^\]]*\]\s*", "", text).strip(),
                             file=os.path.basename(out), duration=dur, phones=phones, durs=durs))
            print(f"{n:02d} plano{si + 1:02d} {spk:12s} {dur:5.2f}s  {clean}")
    json.dump(meta, open(os.path.join(outdir, "lines.json"), "w"), ensure_ascii=False, indent=0)


if __name__ == "__main__":
    build(int(sys.argv[1]), sys.argv[2])
