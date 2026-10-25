"""Kokoro-82M (ONNX, q8) en español, sin red. Uso: tts.py "texto" voz.wav --voice em_alex[:0.7,pm_alex:0.3] --speed 1.0"""
import argparse
import json
import os
import re
import zipfile

import numpy as np
import onnxruntime as ort
import soundfile as sf
from phonemizer.backend import EspeakBackend

M = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
VOCAB = json.load(open(os.path.join(M, "config.json")))["vocab"]
E2M = sorted({
    "a^ɪ": "I", "a^ʊ": "W", "d^z": "ʣ", "d^ʒ": "ʤ", "e^ɪ": "A", "o^ʊ": "O",
    "ə^ʊ": "Q", "s^s": "S", "t^s": "ʦ", "t^ʃ": "ʧ", "ɔ^ɪ": "Y",
}.items())
_backend = None
_sess = None


def phonemize(text):
    global _backend
    if _backend is None:
        _backend = EspeakBackend("es", preserve_punctuation=True, with_stress=True, tie="^",
                                 language_switch="remove-flags")
    text = text.replace("«", "“").replace("»", "”").replace("(", "«").replace(")", "»")
    ps = _backend.phonemize([text])[0].strip()
    for a, b in E2M:
        ps = ps.replace(a, b)
    ps = ps.replace("^", "").replace("«", "(").replace("»", ")")
    return "".join(c for c in ps if c in VOCAB)


def load_voice(name):
    with zipfile.ZipFile(os.path.join(M, "voices", name + ".pt")) as z:
        data = [n for n in z.namelist() if re.search(r"/data/\d+$", n)][0]
        return np.frombuffer(z.read(data), dtype=np.float32).reshape(-1, 1, 256)


def voice_mix(spec):
    """'ef_dora' o 'ef_dora:0.7,pf_dora:0.3'"""
    total, acc = 0.0, None
    for part in spec.split(","):
        n, _, w = part.partition(":")
        w = float(w or 1)
        v = load_voice(n) * w
        acc = v if acc is None else acc + v
        total += w
    return acc / total


def synth(text, voice, speed=1.0):
    global _sess
    if _sess is None:
        so = ort.SessionOptions()
        so.intra_op_num_threads = os.cpu_count()
        _sess = ort.InferenceSession(os.path.join(M, "kokoro-v1.0-q8.onnx"), so, providers=["CPUExecutionProvider"])
    pack = voice_mix(voice)
    chunks = [c for c in re.split(r"(?<=[.!?…])\s+", text) if c.strip()]
    out = []
    for c in chunks:
        ps = phonemize(c)
        ids = [VOCAB[p] for p in ps][:508]
        style = pack[min(len(ids), pack.shape[0] - 1)]
        audio = _sess.run(None, {
            "input_ids": np.array([[0] + ids + [0]], dtype=np.int64),
            "style": style.astype(np.float32),
            "speed": np.array([speed], dtype=np.float32),
        })[0].reshape(-1)
        out.append(audio)
        out.append(np.zeros(int(24000 * 0.18), dtype=np.float32))
    return np.concatenate(out[:-1]) if out else np.zeros(1, np.float32)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("out")
    ap.add_argument("--voice", default="ef_dora")
    ap.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args()
    sf.write(a.out, synth(a.text, a.voice, a.speed), 24000)
    print(phonemize(a.text))
