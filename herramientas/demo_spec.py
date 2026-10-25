"""Especificación de la prueba (parte 1, fragmento) usando las imágenes de referencia del usuario."""
import json
import os
import re

S = "/tmp/claude-0/-home-user/befa3e62-fa66-5b33-842d-0045dda3e47b/scratchpad"
AUD = f"{S}/render/P1/audio"
REF = f"{S}/refs"
lines = {l["n"]: l for l in json.load(open(f"{AUD}/lines.json"))}


def chunks(text, limit=40):
    parts = re.split(r"(?<=[.?!…,:])\s+", text)
    out, cur = [], ""
    for p in parts:
        if cur and len(cur) + 1 + len(p) > limit:
            out.append(cur)
            cur = p
        else:
            cur = (cur + " " + p).strip()
    if cur:
        out.append(cur)
    return out


def line(n, gain=0.0):
    l = dict(lines[n])
    l["file"] = os.path.join(AUD, l["file"])
    l["chunks"] = chunks(l["text"])
    l["gain"] = gain
    return l


def face_from(img, idx=0):
    f = json.load(open(f"{REF}/{img}.face.json"))["faces"][idx]
    return dict(mouth=f["mouth"], chin=f["chin"], eyes=f["eyes"])


BANANA = dict(mouth=dict(center=[375, 437], width=88, angle=0), chin=[375, 505],
              eyes=[dict(center=[343, 376], w=34, h=16), dict(center=[406, 374], w=34, h=16)])
NICO = face_from("320ea8fe-image")
LIA = face_from("a67112d5-image")
LIA["mouth"] = dict(center=[286, 531], width=52, angle=4)
LIA["chin"] = [288, 600]
LIA_CROP = [0.0, 0.15, 0.62, 0.767]

shots = [
    dict(id="plano01", image=f"{REF}/e9b800fd-image.jpg", dur=6.5, fade_in=0.8,
         cam=dict(z0=1.0, z1=1.12, c0=[0.5, 0.42], c1=[0.5, 0.38]), fx=["rain", "lightning", "mist"], grade="night",
         lines=[line(1)], sfx="Lluvia intensa, trueno lejano.", mood="tension"),
    dict(id="plano03", image=f"{REF}/e9b800fd-image.jpg", dur=3.5,
         cam=dict(z0=1.55, z1=1.7, c0=[0.51, 0.33], shake=0.7), fx=["rain"], grade="night",
         faces={"TEO": BANANA}, lines=[line(2)], sfx="Lluvia, respiración, latido.", mood="tension"),
    dict(id="titulo", card=dict(title="EL SABOR DEL MIEDO", subtitle="Parte 1: «Sabor nuevo»"), dur=4.0,
         cam=dict(z0=1.0, z1=1.06), fx=["mist"], lines=[line(4)], sfx="Golpe grave de tráiler.", mood="tension",
         lead=0.9),
    dict(id="plano11", image=f"{REF}/320ea8fe-image.jpg", dur=3.5,
         cam=dict(z0=1.0, z1=1.07, c0=[0.5, 0.5]), fx=["dust"], grade="warm",
         faces={"NICO": NICO}, lines=[line(7)], sfx="Muelles de la cama.", mood="warm"),
    dict(id="plano12", image=f"{REF}/a67112d5-image.jpg", crop=LIA_CROP, dur=4.5,
         cam=dict(z0=1.0, z1=1.06, c0=[0.55, 0.45]), fx=["dust"], grade="warm",
         faces={"LIA": LIA}, lines=[line(8)], sfx="Suspiro.", mood="warm"),
    dict(id="plano13", image=f"{REF}/320ea8fe-image.jpg", dur=6.0,
         cam=dict(z0=1.12, z1=1.22, c0=[0.5, 0.47]), fx=[], grade="warm",
         faces={"NICO": NICO}, lines=[line(9)], sfx="", mood="warm"),
    dict(id="plano15", image=f"{REF}/a67112d5-image.jpg", crop=LIA_CROP, dur=3.5,
         cam=dict(z0=1.35, z1=1.55, c0=[0.6, 0.38]), fx=[], grade="cold",
         faces={"LIA": LIA}, lines=[line(11, -4)], sfx="Golpe grave de tensión.", mood="tension"),
    dict(id="plano17", image=f"{REF}/a67112d5-image.jpg", crop=LIA_CROP, dur=4.5,
         cam=dict(z0=1.15, z1=1.25, c0=[0.58, 0.42]), fx=[], grade="cold",
         faces={"LIA": LIA}, lines=[line(13)], sfx="", mood="tension"),
    dict(id="fin", card=dict(title="CONTINUARÁ…", subtitle="Parte 2: «Turno de noche»"), dur=3.5,
         cam=dict(z0=1.0, z1=1.05), fx=["mist"], fade_out=0.8, sfx="Golpe final grave.", mood="tension"),
]

if __name__ == "__main__":
    json.dump(dict(shots=shots, base_dir=S), open(f"{S}/render/demo_spec.json", "w"), ensure_ascii=False, indent=1)
    print("ok", len(shots))
