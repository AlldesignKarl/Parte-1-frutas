"""Motor de render: convierte una lista de planos (imagen + voces + efectos) en un MP4 vertical.
Uso: python3 render.py spec.json salida.mp4 [--preview]"""
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
from scipy.signal import resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import music as MUSIC  # noqa: E402
import sfx as SFX  # noqa: E402
from mouth import Face, viseme_track  # noqa: E402

W, H, FPS = 1080, 1920, 30
FONT_DIR = os.path.join(HERE, "..", "fonts")
F_SUB = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
F_SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
F_TITLE = os.path.join(FONT_DIR, "creepster.woff")
RNG = np.random.default_rng(3)


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ================================================================== texto
_font_cache = {}


def font(path, size):
    k = (path, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(path, size)
    return _font_cache[k]


def text_layer(lines, fpath, size, fill=(255, 255, 255), stroke=8, stroke_fill=(0, 0, 0), spacing=12, glow=None,
               max_w=W - 120):
    f = font(fpath, size)
    wrapped = []
    for ln in lines:
        words, cur = ln.split(), ""
        for w in words:
            test = (cur + " " + w).strip()
            if f.getlength(test) + 2 * stroke > max_w and cur:
                wrapped.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            wrapped.append(cur)
    asc, desc = f.getmetrics()
    lh = asc + desc + spacing
    tw = int(max(f.getlength(l) for l in wrapped) + 4 * stroke + 40)
    th = int(lh * len(wrapped) + 4 * stroke + 40)
    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(wrapped):
        x = (tw - f.getlength(l)) / 2
        y = 20 + i * lh
        d.text((x, y), l, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=stroke_fill + (255,))
    arr = np.array(img).astype(np.float32)
    if glow:
        a = arr[..., 3]
        g = cv2.GaussianBlur(a, (0, 0), glow[1])
        ga = np.clip(g * glow[2] / 255.0, 0, 1)
        base = np.zeros_like(arr)
        base[..., :3] = glow[0]
        base[..., 3] = ga * 255
        al = arr[..., 3:4] / 255.0
        arr[..., :3] = arr[..., :3] * al + base[..., :3] * (1 - al)
        arr[..., 3] = np.maximum(arr[..., 3], base[..., 3])
    out = arr[..., [2, 1, 0, 3]]  # RGBA -> BGRA
    return out


def blit(frame, layer, cx, cy, alpha=1.0):
    h, w = layer.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    l = layer[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    a = l[..., 3:4] / 255.0 * alpha
    frame[fy0:fy1, fx0:fx1] = frame[fy0:fy1, fx0:fx1] * (1 - a) + l[..., :3] * a


# ================================================================== efectos
class FX:
    def __init__(self, names, dur, seed=0):
        self.names = set(names)
        self.dur = dur
        self.rng = np.random.default_rng(seed)
        r = self.rng
        if "rain" in self.names:
            n = 900
            self.rain = dict(x=r.uniform(-200, W + 200, n), y=r.uniform(-H, H, n), z=r.uniform(0.3, 1.0, n))
        if {"sparks", "shards"} & self.names:
            self.parts = []
        if "dust" in self.names:
            n = 140
            self.dust = dict(x=r.uniform(0, W, n), y=r.uniform(0, H, n), z=r.uniform(0.3, 1, n), ph=r.uniform(0, 6, n))
        self.flick = None
        if {"flicker", "neon_flicker"} & self.names:
            nf = int(dur * FPS) + 2
            f = np.ones(nf, np.float32)
            i = 0
            while i < nf:
                i += int(r.integers(6, 40))
                L = int(r.integers(1, 5))
                f[i:i + L] = r.uniform(0.35, 0.75)
            self.flick = f
        self.flashes = []
        if "lightning" in self.names:
            self.flashes = sorted(r.uniform(0.3, max(0.4, dur - 0.5), 2).tolist())
        if "glitch" in self.names:
            self.glitch_at = sorted(r.uniform(0, dur, int(dur * 1.2)).tolist())

    # -------- capas
    def apply(self, img, t, fi):
        f = img
        n = self.names
        if "cctv" in n:
            g = cv2.cvtColor(f.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
            g = np.clip((g - 128) * 1.25 + 120, 0, 255)
            f = np.stack([g * 0.92, g * 1.0, g * 0.9], -1)
            f *= _SCAN[None if False else slice(None)][..., None] if False else _SCAN[:, None, None]
            f += self.rng.normal(0, 9, (H // 4, W // 4)).repeat(4, 0).repeat(4, 1)[..., None]
        if "glitch" in n:
            near = min([abs(t - g) for g in self.glitch_at] or [9])
            strength = 1.0 if "static_heavy" in n else max(0.0, 1 - near / 0.12)
            if strength > 0:
                f = f.copy()
                for _ in range(int(6 * strength) + 1):
                    y0 = int(self.rng.integers(0, H - 40))
                    hh = int(self.rng.integers(8, 90))
                    f[y0:y0 + hh] = np.roll(f[y0:y0 + hh], int(self.rng.integers(-80, 80)), axis=1)
                if strength > 0.6:
                    f = f * 0.5 + self.rng.uniform(0, 255, (H // 3, W // 3)).repeat(3, 0).repeat(3, 1)[..., None] * 0.5 * strength
        if self.flick is not None:
            f = f * self.flick[min(fi, len(self.flick) - 1)]
        if "neon" in n:
            p = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 0.45)
            f = f * np.array([1.0 + 0.06 * p, 0.97, 1.0 + 0.10 * p], np.float32)
        if "red_alarm" in n:
            p = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 1.0)
            f = f * np.array([0.65 + 0.15 * (1 - p), 0.6 + 0.15 * (1 - p), 1.0 + 0.45 * p], np.float32)
        if "police" in n:
            side = (int(t * 4) % 2)
            m = _GRAD_X if side else _GRAD_X[:, ::-1]
            col = np.array([255, 40, 20] if side else [20, 30, 255], np.float32)
            f = f + m[..., None] * col * 0.35
        if "fog" in n or "mist" in n:
            k = 0.55 if "fog" in n else 0.35
            ox = int(t * 22) % (_FOG.shape[1] - W)
            oy = int(t * 6) % (_FOG.shape[0] - H)
            a = _FOG[oy:oy + H, ox:ox + W] * _BOTTOM * k
            f = f * (1 - a[..., None]) + np.array([225, 222, 215], np.float32) * a[..., None]
        if "frost" in n:
            g = smooth(t / max(self.dur, 0.1)) * 0.6 + 0.25
            a = np.clip((_EDGE - (1 - g)) * 4, 0, 1) * _FROST
            f = f * (1 - a[..., None]) + np.array([255, 245, 225], np.float32) * a[..., None]
            f = f * np.array([1.08, 1.0, 0.9], np.float32)
        if "rain" in n:
            f = self._rain(f, t)
        if "dust" in n:
            d = self.dust
            lay = np.zeros((H, W), np.float32)
            xs = (d["x"] + 12 * np.sin(t * 0.6 + d["ph"])).astype(int) % W
            ys = (d["y"] - t * 18 * d["z"]).astype(int) % H
            for x, y, z in zip(xs, ys, d["z"]):
                cv2.circle(lay, (int(x), int(y)), int(1 + 2 * z), float(120 * z), -1, cv2.LINE_AA)
            lay = cv2.GaussianBlur(lay, (0, 0), 1.5)
            f = f + lay[..., None] * np.array([0.8, 0.9, 1.0], np.float32)
        if {"sparks", "shards"} & n:
            f = self._particles(f, t)
        for fl in self.flashes:
            if 0 <= t - fl < 0.25:
                k = 1 - (t - fl) / 0.25
                f = f * (1 + 1.2 * k) + 40 * k
        return f

    def _rain(self, f, t):
        r = self.rain
        lay = np.zeros((H, W), np.float32)
        speed = 2600 * r["z"]
        ys = (r["y"] + t * speed) % (H + 400) - 200
        xs = r["x"] + (ys + 200) * 0.12
        L = 60 * r["z"]
        segs = [np.array([[x, y], [x + l * 0.12, y + l]], np.int32) for x, y, l in zip(xs, ys, L)]
        thick = [s for s, z in zip(segs, r["z"]) if z > 0.75]
        thin = [s for s, z in zip(segs, r["z"]) if z <= 0.75]
        cv2.polylines(lay, thin, False, 70.0, 1, cv2.LINE_AA)
        cv2.polylines(lay, thick, False, 110.0, 2, cv2.LINE_AA)
        lay = cv2.GaussianBlur(lay, (0, 0), 0.8)
        return f + lay[..., None] * np.array([0.95, 0.95, 0.9], np.float32)

    def _particles(self, f, t):
        r = self.rng
        spark = "sparks" in self.names
        if spark and r.random() < 0.5 or (not spark and t < 0.4):
            k = 12 if spark else 40
            ox, oy = W * r.uniform(0.35, 0.65), H * r.uniform(0.45, 0.62)
            for _ in range(k):
                ang = r.uniform(0, 2 * math.pi)
                sp = r.uniform(300, 1300)
                self.parts.append([ox, oy, math.cos(ang) * sp, math.sin(ang) * sp - 300, t, r.uniform(0.3, 0.9)])
        lay = np.zeros((H, W, 3), np.float32)
        alive = []
        for p in self.parts:
            age = t - p[4]
            if age > p[5]:
                continue
            alive.append(p)
            x = p[0] + p[2] * age
            y = p[1] + p[3] * age + 900 * age * age
            px = p[0] + p[2] * (age - 0.03)
            py = p[1] + p[3] * (age - 0.03) + 900 * (age - 0.03) ** 2
            col = (60, 170, 255) if spark else (255, 250, 240)
            cv2.line(lay, (int(px), int(py)), (int(x), int(y)), col, 2 if spark else 3, cv2.LINE_AA)
        self.parts = alive
        lay = cv2.GaussianBlur(lay, (0, 0), 1.0)
        return f + lay * 1.4


def _make_globals():
    global _FOG, _BOTTOM, _VIG, _GRAIN, _SCAN, _EDGE, _FROST, _GRAD_X
    r = np.random.default_rng(5)
    fh, fw = int(H * 1.6), int(W * 2.2)
    fog = np.zeros((fh, fw), np.float32)
    for s, amp in ((220, 1.0), (90, 0.5), (35, 0.25)):
        small = r.random((fh // s + 2, fw // s + 2)).astype(np.float32)
        fog += cv2.resize(small, (fw, fh), interpolation=cv2.INTER_CUBIC) * amp
    fog = (fog - fog.min()) / (fog.max() - fog.min())
    _FOG = np.clip((fog - 0.35) * 1.6, 0, 1)
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    _BOTTOM = np.clip(0.35 + yy * 0.9, 0, 1) * np.ones((1, W), np.float32)
    yv, xv = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xv - W / 2) / (W * 0.62)) ** 2 + ((yv - H / 2) / (H * 0.62)) ** 2)
    _VIG = np.clip(1.15 - d ** 2 * 0.55, 0.35, 1.0)
    _GRAIN = [r.normal(0, 4.0, (H // 2, W // 2)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(6)]
    _SCAN = (0.86 + 0.14 * (np.arange(H) % 4 < 2)).astype(np.float32)
    _EDGE = np.clip(d * 1.25, 0, 1.2)
    fr = r.random((H // 6, W // 6)).astype(np.float32)
    fr = cv2.resize(fr, (W, H), interpolation=cv2.INTER_NEAREST)
    fr = cv2.GaussianBlur(fr, (0, 0), 2)
    _FROST = np.clip((fr - 0.35) * 2.2, 0, 1) * 0.85
    _GRAD_X = np.clip(1 - np.linspace(0, 1, W, dtype=np.float32) * 1.6, 0, 1)[None, :] * np.ones((H, 1), np.float32)


_make_globals()

GRADES = {
    "cold": (np.array([1.10, 1.0, 0.88], np.float32), 0.95),
    "warm": (np.array([0.88, 0.98, 1.10], np.float32), 1.0),
    "night": (np.array([1.12, 0.98, 0.86], np.float32), 0.9),
    "neutral": (np.array([1.0, 1.0, 1.0], np.float32), 1.0),
}


# ================================================================== imagen y cámara
def load_source(shot, base_dir):
    path = shot.get("image")
    if path and not os.path.isabs(path):
        path = os.path.join(base_dir, path)
    if path and os.path.exists(path):
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        ox = oy = 0
        if shot.get("crop"):
            x0, y0, x1, y1 = shot["crop"]
            ih, iw = img.shape[:2]
            ox, oy = int(x0 * iw), int(y0 * ih)
            img = img[oy:int(y1 * ih), ox:int(x1 * iw)]
        return img, (ox, oy)
    return placeholder(shot), (0, 0)


def placeholder(shot):
    img = np.zeros((H, W, 3), np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    img += np.array([40, 22, 18]) * (1 - yy) + np.array([20, 10, 30]) * yy
    lay = text_layer([shot.get("id", "").upper()], F_SUB, 90, stroke=0)
    blit(img, lay, W / 2, H * 0.4)
    lay = text_layer([shot.get("es", "")], F_SEMI, 44, stroke=0, fill=(200, 200, 200), max_w=W - 200)
    blit(img, lay, W / 2, H * 0.55)
    lay = text_layer(["(falta imagen)"], F_SEMI, 40, stroke=0, fill=(120, 120, 255))
    blit(img, lay, W / 2, H * 0.7)
    return np.clip(img, 0, 255).astype(np.uint8)


def card_background(seed):
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.45) / H) ** 2)
    glow = np.exp(-d * 5)
    img = np.zeros((H, W, 3), np.float32)
    img += np.array([12, 8, 10])
    img += glow[..., None] * np.array([25, 20, 150])
    fog = _FOG[:H, :W] * 40
    img += fog[..., None]
    return np.clip(img, 0, 255).astype(np.uint8)


def camera_matrix(src_shape, cam, t, dur, rng_phase):
    ih, iw = src_shape[:2]
    p = smooth(t / max(dur, 1e-3)) if cam.get("ease", True) else min(t / max(dur, 1e-3), 1)
    z = cam.get("z0", 1.0) + (cam.get("z1", 1.05) - cam.get("z0", 1.0)) * p
    c0, c1 = cam.get("c0", [0.5, 0.5]), cam.get("c1", cam.get("c0", [0.5, 0.5]))
    cx = (c0[0] + (c1[0] - c0[0]) * p) * iw
    cy = (c0[1] + (c1[1] - c0[1]) * p) * ih
    s = max(W / iw, H / ih) * z
    hw, hh = W / 2 / s, H / 2 / s
    cx = min(max(cx, hw), iw - hw) if iw > 2 * hw else iw / 2
    cy = min(max(cy, hh), ih - hh) if ih > 2 * hh else ih / 2
    sh = cam.get("shake", 0.0)
    dx = dy = rot = 0.0
    if sh:
        a, b, c = rng_phase
        dx = sh * 14 * (math.sin(t * 3.1 + a) + 0.5 * math.sin(t * 7.3 + b))
        dy = sh * 14 * (math.sin(t * 2.7 + b) + 0.5 * math.sin(t * 6.1 + c))
        rot = sh * 0.25 * math.sin(t * 1.9 + c)
    for it in cam.get("impacts", []):
        k = t - it
        if 0 <= k < 0.6:
            e = math.exp(-k * 7)
            dx += 30 * e * math.sin(k * 70)
            dy += 22 * e * math.cos(k * 63)
    M = cv2.getRotationMatrix2D((cx, cy), rot, s)
    M[0, 2] += W / 2 - cx + dx
    M[1, 2] += H / 2 - cy + dy
    return M


# ================================================================== clips de vídeo
MPENV_PY = os.path.join(HERE, "..", "mpenv", "bin", "python")


class VideoSource:
    """Clip animado por el usuario: se lee en orden, se adapta a la duración del plano y se sigue la cara."""

    def __init__(self, path, T, order=None):
        self.cap = cv2.VideoCapture(path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        dur = self.n / self.fps
        self.rate = 1.0 if dur >= T else max(0.65, dur / T)  # cámara lenta suave si el clip es corto
        self.idx = -1
        self.img = None
        tj = path + ".faces.json"
        if not os.path.exists(tj):
            subprocess.run([MPENV_PY, os.path.join(HERE, "track_video.py"), path, tj], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.tracks = self._identities(json.load(open(tj))["frames"])

    def _identities(self, frames):
        """Asigna identidad estable a cada cara (por cercanía entre fotogramas) y suaviza su posición."""
        ids, prev = [], []
        next_id = 0
        for faces in frames:
            cur = []
            used = set()
            for f in faces:
                c = np.array(f["center"])
                best, bd = None, 1e9
                for k, (pid, pc) in enumerate(prev):
                    d = np.linalg.norm(c - pc)
                    if d < bd and k not in used:
                        best, bd = k, d
                if best is not None and bd < f["width"] * 2.5:
                    used.add(best)
                    cur.append((prev[best][0], c, f))
                else:
                    cur.append((next_id, c, f))
                    next_id += 1
            ids.append(cur)
            prev = [(i, c) for i, c, _ in cur] or prev
        n = len(frames)
        allid = sorted({i for fr in ids for i, _, _ in fr})
        # orden izquierda→derecha según la posición media
        meanx = {i: np.mean([f["center"][0] for fr in ids for j, _, f in fr if j == i]) for i in allid}
        order = sorted(allid, key=lambda i: meanx[i])
        tracks = []
        for i in order:
            arr = np.full((n, 6), np.nan)
            for k, fr in enumerate(ids):
                for j, _, f in fr:
                    if j == i:
                        arr[k] = [f["center"][0], f["center"][1], f["width"], f["angle"], f["chin"][0], f["chin"][1]]
            ok = ~np.isnan(arr[:, 0])
            if ok.sum() < max(3, n * 0.2):
                continue
            x = np.arange(n)
            for c in range(6):
                arr[:, c] = np.interp(x, x[ok], arr[ok, c])
            k = 5
            ker = np.ones(k) / k
            arr = np.stack([np.convolve(np.pad(arr[:, c], (k // 2, k // 2), mode="edge"), ker, mode="valid")
                            for c in range(6)], 1)
            tracks.append(arr)
        return tracks

    def frame_at(self, t):
        want = min(self.n - 1, int(t * self.rate * self.fps))
        while self.idx < want:
            ok, img = self.cap.read()
            if not ok:
                break
            self.idx += 1
            self.img = img
        return self.img, max(0, self.idx)

    def face_params(self, k, fidx):
        if k >= len(self.tracks):
            return None
        a = self.tracks[k][min(fidx, len(self.tracks[k]) - 1)]
        return dict(center=[a[0], a[1]], width=a[2], angle=a[3], chin=[a[4], a[5]])


# ================================================================== render
def load_line_audio(path):
    a, sr = sf.read(path, dtype="float32")
    if a.ndim > 1:
        a = a.mean(1)
    if sr != SFX.SR:
        g = math.gcd(sr, SFX.SR)
        a = resample_poly(a, SFX.SR // g, sr // g).astype(np.float32)
    return a


def layout(spec):
    t = 0.0
    for s in spec["shots"]:
        lines = s.get("lines", [])
        lead = s.get("lead", 0.45)
        need = lead + sum(l["duration"] for l in lines) + 0.35 * max(0, len(lines) - 1) + s.get("tail", 0.55)
        s["T"] = max(s.get("dur", 3.0), need if lines else 0)
        s["t0"] = t
        tt = lead
        for l in lines:
            l["at"] = tt
            tt += l["duration"] + 0.35
        t += s["T"]
    return t


def build_audio(spec, total, base_dir):
    n = int((total + 1) * SFX.SR)
    voice = np.zeros((n, 2), np.float32)
    beds = np.zeros((n, 2), np.float32)
    hits = np.zeros((n, 2), np.float32)
    segs = []
    for s in spec["shots"]:
        for l in s.get("lines", []):
            a = load_line_audio(os.path.join(base_dir, l["file"]) if not os.path.isabs(l["file"]) else l["file"])
            a *= 10 ** (l.get("gain", 0) / 20)
            st = int((s["t0"] + l["at"]) * SFX.SR)
            e = min(n, st + len(a))
            voice[st:e] += a[: e - st, None]
        for off, a, kind in SFX.events_for(s.get("sfx", ""), s["T"]):
            a = a.astype(np.float32)
            st = int((s["t0"] + off) * SFX.SR)
            if kind == "bed":
                fl = min(len(a) // 3, int(0.25 * SFX.SR))
                if fl > 0:
                    a[:fl] *= np.linspace(0, 1, fl)[:, None]
                    a[-fl:] *= np.linspace(1, 0, fl)[:, None]
                tgt = beds
            else:
                tgt = hits
            e = min(n, st + len(a))
            tgt[st:e] += a[: e - st]
        segs.append((s["t0"], s["t0"] + s["T"], s.get("mood", "tension")))
    # agrupa ánimos consecutivos
    merged = []
    for a, b, m in segs:
        if merged and merged[-1][2] == m:
            merged[-1] = (merged[-1][0], b, m)
        else:
            merged.append((a, b, m))
    mus = MUSIC.score(merged, total).astype(np.float32)[:n]
    if len(mus) < n:
        mus = np.pad(mus, ((0, n - len(mus)), (0, 0)))
    # ducking: baja música y ambientes cuando hay voz
    envv = np.abs(voice[:, 0])
    k = int(0.05 * SFX.SR)
    envv = np.convolve(envv, np.ones(k) / k, mode="same")
    duck = 1 - 0.55 * np.clip(envv / 0.02, 0, 1)
    duck = np.convolve(duck, np.ones(int(0.25 * SFX.SR)) / int(0.25 * SFX.SR), mode="same")[:, None]
    mix = voice * 1.0 + beds * 0.9 * (0.6 + 0.4 * duck) + hits * 0.85 + mus * 0.55 * duck
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    # fundido final
    fe = int(0.8 * SFX.SR)
    end = int(total * SFX.SR)
    mix[max(0, end - fe):end] *= np.linspace(1, 0, min(fe, end))[:, None]
    mix[end:] = 0
    return mix


def render(spec, out_mp4, preview=False):
    base_dir = spec.get("base_dir", os.path.dirname(os.path.abspath(out_mp4)))
    total = layout(spec)
    tmp_wav = out_mp4 + ".wav"
    sf.write(tmp_wav, build_audio(spec, total, base_dir), SFX.SR)
    fps = 15 if preview else FPS
    ow, oh = (W // 2, H // 2) if preview else (W, H)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{ow}x{oh}",
                           "-r", str(fps), "-i", "-", "-i", tmp_wav, "-c:v", "libx264", "-preset",
                           "veryfast" if preview else "medium", "-crf", "26" if preview else "23", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_mp4],
                          stdin=subprocess.PIPE)
    gi = 0
    for si, s in enumerate(spec["shots"]):
        T = s["T"]
        nfr = int(round(T * fps))
        vsrc = None
        if s.get("video"):
            vp = s["video"] if os.path.isabs(s["video"]) else os.path.join(base_dir, s["video"])
            vsrc = VideoSource(vp, T)
            src, (ox, oy) = vsrc.frame_at(0)[0], (0, 0)
        else:
            src, (ox, oy) = (card_background(si), (0, 0)) if (s.get("card") and not s.get("image")) else load_source(s, base_dir)
        faces = {}
        for spk, fd in (s.get("faces") or {}).items():
            m = fd["mouth"]
            faces[spk] = Face([m["center"][0] - ox, m["center"][1] - oy], m["width"], m.get("angle", 0),
                              chin=[fd["chin"][0] - ox, fd["chin"][1] - oy] if fd.get("chin") else None,
                              eyes=[dict(e, center=[e["center"][0] - ox, e["center"][1] - oy]) for e in fd.get("eyes", [])],
                              open_scale=fd.get("open_scale", 1.0), blink=fd.get("blink", False), seed=si * 7 + len(spk))
        speakers_order = s.get("faces_order") or []
        if vsrc is not None:
            for l in s.get("lines", []):
                if l.get("mode") in ("on", "tv") and l["speaker"] not in faces:
                    faces[l["speaker"]] = "video"
        tracks = {}
        for l in s.get("lines", []):
            if l.get("mode") in ("on", "tv") and l["speaker"] in faces:
                o, sp = viseme_track(l["phones"], l["durs"], fps, nfr, offset_s=l["at"])
                if l["speaker"] in tracks:
                    tracks[l["speaker"]] = (tracks[l["speaker"]][0] + o, tracks[l["speaker"]][1] + sp)
                else:
                    tracks[l["speaker"]] = (o, sp)
        fx = FX(s.get("fx", []), T, seed=si)
        grade, gamma = GRADES.get(s.get("grade", "neutral"), GRADES["neutral"])
        cam = s.get("cam", {})
        phase = np.random.default_rng(si).uniform(0, 6, 3)
        subs = []
        for l in s.get("lines", []):
            if spec.get("subtitles", False) and l.get("text") and not s.get("card"):
                chunks = l.get("chunks") or [l["text"]]
                per = l["duration"] / len(chunks)
                for ci, c in enumerate(chunks):
                    subs.append((l["at"] + ci * per, l["at"] + (ci + 1) * per, text_layer([c], F_SUB, 64, stroke=9)))
        card_layers = []
        if s.get("card"):
            c = s["card"]
            card_layers.append(text_layer([c["title"]], F_TITLE, 150, fill=(235, 30, 30), stroke=4,
                                          stroke_fill=(20, 0, 0), glow=((40, 40, 255), 18, 1.4)))
            if c.get("subtitle"):
                card_layers.append(text_layer([c["subtitle"]], F_SUB, 66, stroke=6))
        note_layer = text_layer([s["note"]], F_SEMI, 50, fill=(30, 30, 30), stroke=0, max_w=W - 260) if s.get("note") else None
        for fi in range(nfr):
            t = fi / fps
            img = src
            vfi = 0
            if vsrc is not None:
                img, vfi = vsrc.frame_at(t)
            for spk, face in faces.items():
                if face == "video":
                    k = speakers_order.index(spk) if spk in speakers_order else 0
                    fp = vsrc.face_params(k, vfi)
                    if fp is None or spk not in tracks:
                        continue
                    o, sp = tracks[spk]
                    img = Face(fp["center"], fp["width"], fp["angle"], chin=fp["chin"]).apply_mouth(img, float(o[fi]), float(sp[fi]))
                    continue
                if spk in tracks:
                    o, sp = tracks[spk]
                    img = face.apply_mouth(img, float(o[fi]), float(sp[fi]))
                img = face.apply_blink(img, face.blink_amount(t + si * 1.7))
            M = camera_matrix(img.shape, cam, t, T, phase)
            fr = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
            fr = fx.apply(fr, t, fi)
            fr = fr * grade
            if gamma != 1.0:
                fr = 255 * (np.clip(fr, 0, 255) / 255) ** (1 / gamma)
            fr = fr * _VIG[..., None] + _GRAIN[(gi + fi) % 6][..., None]
            if "cctv" in s.get("fx", []):
                stamp = text_layer([f"CAM 04   REC ●   00:13:{int(t) % 60:02d}"], F_SEMI, 40, stroke=3)
                blit(fr, stamp, W / 2, 130)
            for k, layer in enumerate(card_layers):
                a = smooth(t / 0.6) * smooth((T - t) / 0.5)
                blit(fr, layer, W / 2, H * (0.44 if k == 0 else 0.56), a)
            if note_layer is not None and t > 0.8:
                box = np.zeros((note_layer.shape[0] + 40, note_layer.shape[1] + 60, 4), np.float32)
                box[..., :3] = (225, 238, 245)
                box[..., 3] = 235
                blit(fr, box, W / 2, H * 0.62, smooth((t - 0.8) / 0.4))
                blit(fr, note_layer, W / 2, H * 0.62, smooth((t - 0.8) / 0.4))
            for a0, a1, layer in subs:
                if a0 <= t < a1:
                    blit(fr, layer, W / 2, H * 0.73)
            fade = 1.0
            if s.get("fade_in"):
                fade *= smooth(t / s["fade_in"])
            if s.get("fade_out"):
                fade *= smooth((T - t) / s["fade_out"])
            if s.get("cut_black") and t > T - s["cut_black"]:
                fade = 0.0
            if fade < 1:
                fr *= fade
            fr = np.clip(fr, 0, 255).astype(np.uint8)
            if preview:
                fr = cv2.resize(fr, (ow, oh), interpolation=cv2.INTER_AREA)
            ff.stdin.write(fr.tobytes())
        gi += nfr
        print(f"  plano {si + 1:02d}/{len(spec['shots'])}  {T:.1f}s", flush=True)
    ff.stdin.close()
    ff.wait()
    os.remove(tmp_wav)
    print("OK", out_mp4, f"{total:.1f}s")


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    render(spec, sys.argv[2], preview="--preview" in sys.argv)
