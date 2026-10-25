"""Efectos de sonido sintetizados (48 kHz, estéreo) y su asignación a partir de las notas «Sonido» del guion."""
import re

import numpy as np
from scipy import signal

SR = 48000
RNG = np.random.default_rng(7)


def t_(d):
    return np.arange(int(d * SR)) / SR


def stereo(x, width=0.0):
    if x.ndim == 2:
        return x
    if width <= 0:
        return np.stack([x, x], 1)
    d = int(SR * 0.012 * width)
    y = np.concatenate([np.zeros(d), x[:-d]]) if d else x
    return np.stack([x, y], 1)


def noise(d, color="white", rng=RNG):
    n = int(d * SR)
    w = rng.standard_normal(n)
    if color == "white":
        return w
    f = np.fft.rfft(w)
    k = np.arange(len(f)) + 1.0
    f /= np.sqrt(k) if color == "pink" else k
    x = np.fft.irfft(f, n)
    return x / (np.abs(x).max() + 1e-9)


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="low", fs=SR, output="sos"), x, axis=0)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="high", fs=SR, output="sos"), x, axis=0)


def env(n, a=0.005, r=0.3, shape=2.0):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-np.maximum(t - a, 0) / max(r, 1e-4) * shape)
    return e


def norm(x, db):
    p = np.abs(x).max() + 1e-9
    return x / p * 10 ** (db / 20)


_IR = {}


def reverb(x, size=1.8, mix=0.3):
    key = round(size, 2)
    if key not in _IR:
        n = int(SR * size)
        ir = np.stack([noise(size, "white", np.random.default_rng(1)), noise(size, "white", np.random.default_rng(2))], 1)
        ir *= np.exp(-np.arange(n) / SR * 6.0 / size)[:, None]
        ir = lp(ir, 6000)
        _IR[key] = ir / np.sqrt((ir ** 2).sum(0))
    ir = _IR[key]
    xs = stereo(x)
    wet = np.stack([signal.fftconvolve(xs[:, c], ir[:, c])[:len(xs) + len(ir) - 1] for c in range(2)], 1)
    out = np.zeros_like(wet)
    out[:len(xs)] += xs * (1 - mix)
    out += wet * mix
    return out


# ---------------------------------------------------------------------------------------------- sonidos
def rain(d):
    a = bp(noise(d, "pink"), 300, 9000) * 0.6
    drops = np.zeros(int(d * SR))
    idx = RNG.integers(0, len(drops), int(d * 900))
    drops[idx] = RNG.uniform(-1, 1, len(idx))
    drops = bp(drops, 1500, 7000)
    b = bp(noise(d, "pink"), 300, 9000) * 0.6
    return norm(np.stack([a + drops * 0.5, b + np.roll(drops, 311) * 0.5], 1), -24)


def wind(d):
    t = t_(d)
    x = noise(d, "pink")
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t + 1.0)
    y = bp(x, 180, 900) * lfo
    return norm(stereo(y, 1), -27)


def thunder(d=6.0):
    n = int(d * SR)
    crack = bp(noise(0.5), 300, 3000) * env(int(0.5 * SR), 0.002, 0.15)
    rumble = lp(noise(d, "brown"), 140) * env(n, 0.25, d * 0.45, 1.5)
    rumble *= 1 + 0.5 * lp(RNG.standard_normal(n), 3)[: n] / 0.05
    y = np.zeros(n)
    y[:len(crack)] += crack * 0.6
    y += rumble
    return norm(reverb(y, 2.5, 0.35), -14)


def hum(d, f=100):
    t = t_(d)
    y = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.3 for k in range(1, 8))
    y += 0.05 * noise(d)
    return norm(stereo(y), -34)


def buzz(d):
    t = t_(d)
    y = np.sign(np.sin(2 * np.pi * 100 * t)) * 0.3 + noise(d) * 0.2
    gate = (lp(RNG.standard_normal(len(t)), 8) > 0).astype(float)
    return norm(stereo(hp(y * gate, 200)), -28)


def boom(d=3.0):
    t = t_(d)
    f = 95 * np.exp(-t * 1.4) + 32
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(ph) * env(len(t), 0.004, 1.2, 1.3)
    hit = lp(noise(d), 900) * env(len(t), 0.002, 0.12)
    braam = sum(np.sign(np.sin(2 * np.pi * 55 * (1 + det) * t)) for det in (-0.006, 0, 0.007)) / 3
    braam = lp(braam, 500) * env(len(t), 0.03, 0.9, 1.2) * 0.35
    return norm(reverb(sub + hit * 0.7 + braam, 2.8, 0.35), -9)


def stinger(d=2.5):
    t = t_(d)
    cl = sum(np.sin(2 * np.pi * f * t + RNG.uniform(0, 6)) for f in (880, 932.3, 987.8, 1244.5))
    cl *= env(len(t), 0.01, 0.6)
    return norm(reverb(cl * 0.5 + boom(d)[:, 0] * 2, 2.5, 0.4), -10)


def clang(d=2.5):
    t = t_(d)
    y = sum(np.sin(2 * np.pi * 420 * r * t) * np.exp(-t * (2.0 + 1.3 * i)) / (i + 1) for i, r in
            enumerate([1, 2.76, 5.40, 8.93, 13.34]))
    y += hp(noise(d), 2000) * env(len(t), 0.001, 0.03)
    return norm(reverb(y, 1.6, 0.35), -11)


def slam(d=2.0):
    t = t_(d)
    y = np.sin(2 * np.pi * 58 * t) * env(len(t), 0.002, 0.25) + lp(noise(d), 700) * env(len(t), 0.001, 0.15)
    return norm(reverb(y, 2.0, 0.4), -10)


def static(d):
    y = bp(noise(d), 800, 9000)
    gate = 0.6 + 0.4 * (lp(RNG.standard_normal(len(y)), 20) > 0)
    return norm(stereo(y * gate), -26)


def hiss(d):
    y = hp(noise(d), 3000) * env(int(d * SR), 0.15, d * 0.6, 1.2)
    return norm(stereo(y, 1), -26)


def footsteps(d, rate=1.9, wet=False):
    n = int(d * SR)
    y = np.zeros(n)
    step = int(SR / rate)
    for k, s in enumerate(range(int(0.1 * SR), n - int(0.2 * SR), step)):
        m = int(0.12 * SR)
        thud = lp(noise(0.12), 300 + 80 * (k % 2)) * env(m, 0.002, 0.04)
        y[s:s + m] += thud[: n - s]
        if wet:
            sp = bp(noise(0.25), 800, 5000) * env(int(0.25 * SR), 0.005, 0.08)
            y[s:s + len(sp)] += sp[: n - s] * 0.5
    return norm(reverb(y, 1.2, 0.25), -20)


def heartbeat(d, bpm=70):
    n = int(d * SR)
    y = np.zeros(n)
    per = int(SR * 60 / bpm)
    m = int(0.25 * SR)
    beat = np.sin(2 * np.pi * 52 * t_(0.25)) * env(m, 0.004, 0.06)
    for s in range(0, n - m, per):
        y[s:s + m] += beat
        s2 = s + int(0.24 * SR)
        if s2 + m < n:
            y[s2:s2 + m] += beat * 0.7
    return norm(stereo(y), -12)


def tick(d):
    n = int(d * SR)
    y = np.zeros(n)
    for k, s in enumerate(range(0, n - 2000, SR)):
        c = bp(noise(0.02), 2500 if k % 2 else 3200, 7000) * env(int(0.02 * SR), 0.0005, 0.004)
        y[s:s + len(c)] += c
    return norm(reverb(y, 0.8, 0.2), -26)


def siren(d):
    t = t_(d)
    f = np.where((t % 1.0) < 0.5, 650, 850) * (1 + 0.003 * np.sin(2 * np.pi * 6 * t))
    y = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR, 0.5)
    return norm(reverb(lp(y, 2500), 2.0, 0.5), -24)


def alarm(d):
    t = t_(d)
    y = np.sign(np.sin(2 * np.pi * 880 * t)) * ((t % 0.5) < 0.25)
    return norm(reverb(lp(y, 3000), 1.5, 0.4), -27)


def beep(d=0.4):
    t = t_(d)
    return norm(stereo(np.sin(2 * np.pi * 1250 * t) * (t < 0.15)), -24)


def click(d=0.2):
    return norm(stereo(hp(noise(d), 1500) * env(int(d * SR), 0.0005, 0.01)), -20)


def crowd(d):
    t = t_(d)
    y = np.zeros(len(t))
    for k in range(10):
        syl = (lp(RNG.standard_normal(len(t)), 5) > 0.02).astype(float)
        syl = lp(syl, 12)
        y += bp(noise(d, "pink"), 250 + 40 * k, 2200) * syl
    return norm(reverb(y, 2.2, 0.5), -28)


def applause(d=3.0):
    n = int(d * SR)
    y = np.zeros(n)
    idx = RNG.integers(0, n, int(d * 2500))
    y[idx] = RNG.uniform(-1, 1, len(idx))
    y = bp(y, 900, 7000) * env(n, 0.3, d * 0.6, 1.0)
    return norm(reverb(y, 1.8, 0.4), -22)


def drips(d):
    n = int(d * SR)
    y = np.zeros(n)
    for s in RNG.integers(0, max(1, n - SR // 10), max(1, int(d * 0.9))):
        tt = t_(0.06)
        c = np.sin(2 * np.pi * np.cumsum(1600 * np.exp(-tt * 18) + 700) / SR) * env(len(tt), 0.001, 0.02)
        y[s:s + len(c)] += c
    return norm(reverb(y, 1.5, 0.5), -26)


def motor(d, f=48, whine=False):
    t = t_(d)
    y = signal.sawtooth(2 * np.pi * f * t) * 0.6 + lp(noise(d), 400) * 0.3
    if whine:
        y += np.sin(2 * np.pi * 330 * t + 3 * np.sin(2 * np.pi * 7 * t)) * 0.25
    return norm(stereo(lp(y, 1800)), -24)


def whoosh(d=0.8):
    n = int(d * SR)
    x = noise(d)
    out = np.zeros(n)
    for i, f in enumerate(np.linspace(300, 3000, 8)):
        seg = slice(i * n // 8, (i + 1) * n // 8)
        out[seg] = bp(x, f * 0.7, f * 1.3)[seg]
    return norm(stereo(out * np.hanning(n), 1), -20)


def crackle(d):
    n = int(d * SR)
    y = np.zeros(n)
    idx = RNG.integers(0, n, int(d * 120))
    y[idx] = RNG.uniform(-1, 1, len(idx))
    return norm(stereo(hp(y, 2500)), -22)


def ring(d=2.0):
    t = t_(d)
    y = (np.sin(2 * np.pi * 440 * t) + np.sin(2 * np.pi * 480 * t)) * ((t % 1.0) < 0.6)
    return norm(stereo(bp(y, 300, 3400)), -26)


def ice(d=1.5):
    y = crackle(d)[:, 0] * 2 + lp(noise(d, "brown"), 200) * 0.5 * env(int(d * SR), 0.05, d * 0.5)
    return norm(reverb(y, 1.5, 0.3), -18)


# ----------------------------------------------------------------- reglas: texto de «Sonido» -> eventos
# (patrón, función, tipo) — tipo: 'bed' cubre todo el plano; 'hit' suena una vez; 'end' al final del plano
RULES = [
    (r"lluvia", lambda d: rain(d), "bed"),
    (r"viento", lambda d: wind(d), "bed"),
    (r"trueno", lambda d: thunder(min(6, d + 2)), "hit"),
    (r"zumbido|neón|monitores|fluorescente", lambda d: hum(d), "bed"),
    (r"chisporroteo|eléctric", lambda d: buzz(d), "bed"),
    (r"golpe final|golpe grave final", lambda d: boom(3.0), "end"),
    (r"golpe de terror|stinger", lambda d: stinger(2.5), "hit"),
    (r"golpe grave|golpe de tensión|impacto de tensión|golpe seco|nota grave", lambda d: boom(3.0), "hit"),
    (r"clang|metálic|engranaje|chirrido", lambda d: clang(2.5), "hit"),
    (r"portazo|¡bum|golpe en la mesa|codazo|golpe,", lambda d: slam(2.0), "hit"),
    (r"estática", lambda d: static(d), "bed"),
    (r"siseo|frío|congelaci|vapor|aire helado", lambda d: hiss(d), "bed"),
    (r"pisadas en el agua|charco", lambda d: footsteps(d, 2.6, True), "bed"),
    (r"pasos|pisadas|tacones", lambda d: footsteps(d, 1.8), "bed"),
    (r"latido", lambda d: heartbeat(d), "bed"),
    (r"tic-tac|reloj", lambda d: tick(d), "bed"),
    (r"sirena", lambda d: siren(d), "bed"),
    (r"alarma", lambda d: alarm(d), "bed"),
    (r"pitido", lambda d: beep(), "hit"),
    (r"clic|toque en la pantalla", lambda d: click(), "hit"),
    (r"murmullo|gente|ambiente del centro", lambda d: crowd(d), "bed"),
    (r"aplausos|flashes", lambda d: applause(min(d, 3.0)), "hit"),
    (r"goteo|gotea", lambda d: drips(d), "bed"),
    (r"licuadora", lambda d: motor(d, 60, True), "bed"),
    (r"motor|maquinaria|cinta transportadora", lambda d: motor(d, 46), "bed"),
    (r"chispas|crujido|hielo", lambda d: ice(min(d, 2.0)), "hit"),
    (r"tono de llamada", lambda d: ring(min(d, 2.0)), "hit"),
    (r"papel|roce", lambda d: crackle(min(d, 1.2)) * 0.5, "hit"),
]


def events_for(text, dur):
    """Devuelve [(offset_s, audio)] para un plano según su descripción de sonido."""
    t = (text or "").lower()
    out = []
    used = set()
    for pat, fn, kind in RULES:
        if re.search(pat, t) and fn not in used:
            used.add(fn)
            a = fn(dur)
            if kind == "bed":
                out.append((0.0, a[: int(dur * SR)], "bed"))
            elif kind == "end":
                out.append((max(0.0, dur - 0.6), a, "hit"))
            else:
                out.append((0.15, a, "hit"))
    return out
