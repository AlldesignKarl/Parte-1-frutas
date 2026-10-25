"""Chatterbox Multilingual (CPU) en español. Lee un JSON de trabajos y genera los WAV.
  cbenv/bin/python cb_tts.py jobs.json
jobs.json: [{"text":..., "out":..., "ref": wav|null, "exaggeration":0.5, "cfg":0.5, "temperature":0.8, "seed":1}]"""
import json
import os
import sys
import time

import torch
import torchaudio as ta

torch.set_num_threads(os.cpu_count())
CKPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "cb")


def main(path):
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    jobs = json.load(open(path))
    model = ChatterboxMultilingualTTS.from_local(CKPT, "cpu")
    for j in jobs:
        if os.path.exists(j["out"]) and not j.get("force"):
            continue
        torch.manual_seed(j.get("seed", 1))
        t0 = time.time()
        wav = model.generate(j["text"], language_id="es", audio_prompt_path=j.get("ref"),
                             exaggeration=j.get("exaggeration", 0.5), cfg_weight=j.get("cfg", 0.5),
                             temperature=j.get("temperature", 0.8))
        ta.save(j["out"], wav, model.sr)
        print(f"{time.time() - t0:5.1f}s  {wav.shape[-1] / model.sr:5.2f}s audio  {os.path.basename(j['out'])}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
