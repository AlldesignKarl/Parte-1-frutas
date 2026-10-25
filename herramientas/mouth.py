"""Animación de boca (lip-sync por visemas) y parpadeo sobre una imagen fija, mediante deformación local."""
import math

import cv2
import numpy as np

# Visemas: (apertura 0..1, ensanche -1 redonda .. +1 estirada)
VISEME = {
    "A": (1.0, 0.15), "E": (0.6, 0.45), "I": (0.32, 0.65), "O": (0.72, -0.55), "U": (0.36, -0.85),
    "M": (0.0, 0.0), "F": (0.12, 0.2), "C": (0.28, 0.15), "REST": (0.0, 0.0),
}
VOWELS = {"a": "A", "e": "E", "ɛ": "E", "i": "I", "j": "I", "o": "O", "ɔ": "O", "u": "U", "w": "U", "ə": "E"}
BILABIAL = set("mbpβ")
LABIODENTAL = set("fv")
SILENT = set(" .,;:!?¡¿…—\"“”()ˈˌ-")


def phone_viseme(p):
    if p in VOWELS:
        return VOWELS[p]
    if p in BILABIAL:
        return "M"
    if p in LABIODENTAL:
        return "F"
    if p in SILENT:
        return "REST"
    return "C"


def viseme_track(phones, durs, fps, total_frames, offset_s=0.0, sec_per_unit=0.025):
    """Devuelve arrays (apertura, ensanche) por fotograma a partir de fonemas y duraciones del TTS."""
    keys = []  # (t_centro, open, spread)
    t = offset_s
    for p, d in zip(phones, durs):
        dur = d * sec_per_unit
        v = VISEME[phone_viseme(p)]
        if dur > 0:
            keys.append((t + dur * 0.5, v[0], v[1], dur))
        t += dur
    op = np.zeros(total_frames, np.float32)
    sp = np.zeros(total_frames, np.float32)
    if not keys:
        return op, sp
    kt = np.array([k[0] for k in keys])
    ko = np.array([k[1] for k in keys])
    ks = np.array([k[2] for k in keys])
    ft = np.arange(total_frames) / fps
    o = np.interp(ft, kt, ko, left=0, right=0)
    s = np.interp(ft, kt, ks, left=0, right=0)
    # fuera del rango del habla, boca en reposo
    start, end = offset_s, t
    mask = (ft >= start - 0.05) & (ft <= end + 0.05)
    o *= mask
    s *= mask
    # suavizado (coarticulación)
    k = max(1, int(fps * 0.06))
    ker = np.hanning(2 * k + 1)
    ker /= ker.sum()
    o = np.convolve(o, ker, mode="same")
    s = np.convolve(s, ker, mode="same")
    return o.astype(np.float32), s.astype(np.float32)


class Face:
    def __init__(self, mouth_center, mouth_width, angle=0.0, chin=None, eyes=None, open_scale=1.0,
                 interior=(22, 16, 52), teeth=True, blink=False, seed=0):
        self.c = np.array(mouth_center, np.float32)
        self.w = float(mouth_width)
        self.a = math.radians(angle)
        self.chin_d = float(np.linalg.norm(np.array(chin) - self.c)) if chin is not None else self.w * 1.1
        self.chin_d = max(self.chin_d, self.w * 0.6)
        self.eyes = eyes or []
        self.open_scale = open_scale
        self.interior = np.array(interior, np.float32)  # BGR
        self.teeth = teeth
        self.blink = blink
        rng = np.random.default_rng(seed)
        self.blink_times = np.cumsum(rng.uniform(2.2, 5.0, 200))
        self._lid_color = None

    # ---------------------------------------------------------------- boca
    def apply_mouth(self, img, open_, spread):
        if open_ < 0.01 and abs(spread) < 0.02:
            return img
        w = self.w
        rx = int(w * 1.5)
        ry0 = int(w * 0.9)
        ry1 = int(self.chin_d * 1.5 + w * 0.3)
        cx, cy = self.c
        R = int(max(rx, ry0, ry1)) + 4
        x0, y0 = int(cx - R), int(cy - R)
        x1, y1 = int(cx + R), int(cy + R)
        H, W = img.shape[:2]
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            pad = R + 2
            big = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REFLECT)
            out = self._mouth_crop(big, cx + pad, cy + pad, R, open_, spread)
            return out[pad:pad + H, pad:pad + W]
        return self._mouth_crop(img, cx, cy, R, open_, spread)

    def _mouth_crop(self, img, cx, cy, R, open_, spread):
        x0, y0 = int(cx - R), int(cy - R)
        size = 2 * R
        crop = img[y0:y0 + size, x0:x0 + size].astype(np.float32)
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
        dx = xx + x0 - cx
        dy = yy + y0 - cy
        ca, sa = math.cos(self.a), math.sin(self.a)
        u = dx * ca + dy * sa          # a lo largo de la boca
        v = -dx * sa + dy * ca         # hacia abajo
        w = self.w * (1 + 0.12 * spread)
        hmax = 0.42 * self.w * self.open_scale
        op = float(np.clip(open_, 0, 1.2))
        lens = np.sqrt(np.clip(1 - (2 * u / w) ** 2, 0, 1))
        down = hmax * op * lens
        up = 0.22 * down
        # mandíbula y labio inferior bajan; caída suave hasta la barbilla
        jaw_w = np.exp(-(u / (self.w * 0.95)) ** 4)
        fall = np.clip(1 - (v / (self.chin_d * 1.35)), 0, 1) ** 1.2
        Dl = (hmax * op * (0.55 + 0.45 * lens)) * jaw_w * fall
        fall_up = np.clip(1 + v / (self.w * 0.45), 0, 1)
        Du = up * fall_up
        vs = np.where(v >= 0, v - Dl, v + Du)
        # estirar/redondear
        g = np.exp(-(u / (self.w * 0.9)) ** 2 - (v / (self.w * 0.55)) ** 2)
        us = u * (1 - 0.14 * spread * g)
        sx = us * ca - vs * sa + cx - x0
        sy = us * sa + vs * ca + cy - y0
        warped = cv2.remap(crop, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        # interior de la boca
        f = 1.4
        inside = (np.clip((down - v) / f, 0, 1) * np.clip((v + up) / f, 0, 1) *
                  np.clip((w / 2 - np.abs(u)) / f, 0, 1))
        if op > 0.02:
            depth = np.clip(1 - np.abs(u) / (w / 2), 0, 1)
            col = np.empty_like(warped)
            base = self.interior
            col[:] = base
            col *= (0.55 + 0.45 * (1 - depth))[..., None]
            if self.teeth and op > 0.22:
                th = 0.28 * hmax * min(op, 1)
                tmask = np.clip((-up + th - v) / 1.5, 0, 1) * np.clip((v + up) / 1.0, 0, 1) * \
                    np.clip((w * 0.36 - np.abs(u)) / 2.0, 0, 1)
                tcol = np.array([205, 212, 218], np.float32) * (0.75 + 0.25 * depth)[..., None]
                col = col * (1 - 0.9 * tmask[..., None]) + tcol * (0.9 * tmask[..., None])
            tongue = np.clip((v - (down * 0.45)) / 2.0, 0, 1) * np.clip((w * 0.3 - np.abs(u)) / 3.0, 0, 1) * (op > 0.35)
            col = col * (1 - 0.45 * tongue[..., None]) + np.array([45, 40, 105], np.float32) * (0.45 * tongue[..., None])
            a = cv2.GaussianBlur(inside, (0, 0), 0.8)[..., None]
            warped = warped * (1 - a) + col * a
        out = img.copy()
        out[y0:y0 + size, x0:x0 + size] = np.clip(warped, 0, 255).astype(img.dtype)
        return out

    # ---------------------------------------------------------------- ojos
    def blink_amount(self, t):
        if not self.blink or not self.eyes:
            return 0.0
        i = np.searchsorted(self.blink_times, t)
        best = 0.0
        for j in (i - 1, i):
            if 0 <= j < len(self.blink_times):
                d = abs(t - self.blink_times[j])
                if d < 0.09:
                    best = max(best, 1 - d / 0.09)
        return best

    def apply_blink(self, img, amount):
        """Cierra el párpado estirando hacia abajo la piel que hay encima del ojo (conserva la textura)."""
        if amount <= 0.01:
            return img
        out = img.copy()
        H, W = img.shape[:2]
        for e in self.eyes:
            cx, cy = e["center"]
            hw = e["w"] * 0.62
            he = max(e["h"] * 0.6, e["w"] * 0.22)
            m = he * 0.9
            top = cy - he - m
            x0, x1 = int(cx - hw - 4), int(cx + hw + 4)
            y0, y1 = int(top - 2), int(cy + he + 4)
            if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
                continue
            crop = img[y0:y1, x0:x1].astype(np.float32)
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            nx = (xx - cx) / hw
            win = np.clip((1 - nx ** 2) * 3, 0, 1)
            L = (cy - he) + 2 * he * 0.95 * amount * win
            span = np.maximum(L - top, 1e-3)
            ys = np.where(yy < L, top + (yy - top) * (m / span), yy)
            ys = np.where(yy < top, yy, ys)
            res = cv2.remap(img.astype(np.float32), xx, ys.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            lash = np.exp(-((yy - L) / max(1.2, he * 0.12)) ** 2) * win * (amount > 0.2)
            res = res * (1 - 0.5 * lash[..., None])
            a = np.clip(win * 1.5, 0, 1)[..., None]
            out[y0:y1, x0:x1] = np.clip(crop * (1 - a) + res * a, 0, 255).astype(img.dtype)
        return out
