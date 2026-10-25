"""Música de fondo sintetizada por estados de ánimo (48 kHz estéreo).
Ánimos: tension, warm, action, emotional, sinister, none."""
import numpy as np
from scipy import signal

from sfx import SR, env, lp, noise, reverb

RNG = np.random.default_rng(11)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def saw_pad(freqs, d, cutoff=900, det=0.004):
    t = np.arange(int(d * SR)) / SR
    y = np.zeros(len(t))
    for f in freqs:
        for k in (-1, 0, 1):
            y += signal.sawtooth(2 * np.pi * f * (1 + k * det) * t + RNG.uniform(0, 6))
    return lp(y / (3 * len(freqs)), cutoff)


def piano(f, d=3.0, vel=1.0):
    t = np.arange(int(d * SR)) / SR
    y = sum(np.sin(2 * np.pi * f * k * t * (1 + 0.0004 * k * k)) * np.exp(-t * (1.2 + 0.9 * k)) / k ** 1.4
            for k in range(1, 7))
    return y * env(len(t), 0.003, d * 0.5, 1.0) * vel


def bell(f, d=2.5, vel=1.0):
    t = np.arange(int(d * SR)) / SR
    mod = np.sin(2 * np.pi * f * 3.5 * t) * 2.2 * np.exp(-t * 3)
    return np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 2.2) * vel


def place(buf, x, start):
    s = int(start * SR)
    if s >= len(buf):
        return
    e = min(len(buf), s + len(x))
    buf[s:e] += x[: e - s]


def tension(d):
    t = np.arange(int(d * SR)) / SR
    y = saw_pad([midi(33), midi(40)], d, 300) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.07 * t))
    hi = sum(np.sin(2 * np.pi * midi(n) * t) for n in (81, 82)) * 0.05
    hi *= 0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t - 1.5)
    y = y + hi
    s = 1.0
    while s < d - 1:
        place(y, piano(midi(RNG.choice([45, 44, 48, 41])), 4.0, 0.35), s)
        s += RNG.uniform(3.5, 6.0)
    return y


def warm(d):
    y = np.zeros(int(d * SR))
    prog = [[48, 52, 55, 59], [45, 48, 52, 55], [41, 45, 48, 52], [43, 47, 50, 55]]
    s, i = 0.0, 0
    while s < d:
        ch = prog[i % 4]
        place(y, saw_pad([midi(n) for n in ch], 4.2, 1100) * env(int(4.2 * SR), 0.6, 3.0, 0.8) * 0.6, s)
        for j, n in enumerate(ch + [ch[1] + 12]):
            place(y, piano(midi(n + 12), 2.5, 0.25), s + j * 0.5)
        s += 4.0
        i += 1
    return y


def action(d, bpm=138):
    y = np.zeros(int(d * SR))
    step = 60 / bpm / 4
    pat = [33, 33, 36, 33, 33, 38, 33, 36]
    k, s = 0, 0.0
    while s < d:
        f = midi(pat[k % len(pat)])
        tt = np.arange(int(step * SR)) / SR
        note = lp(signal.sawtooth(2 * np.pi * f * tt), 700) * np.exp(-tt * 10) * 0.6
        place(y, note, s)
        if k % 8 == 0:
            place(y, lp(noise(0.5), 160) * env(int(0.5 * SR), 0.002, 0.15) * 1.4, s)
        s += step
        k += 1
    y += tension(d) * 0.5
    return y


def emotional(d):
    y = np.zeros(int(d * SR))
    prog = [[45, 52, 57, 60], [41, 48, 53, 57], [48, 55, 60, 64], [43, 50, 55, 59]]
    s, i = 0.0, 0
    while s < d:
        ch = prog[i % 4]
        place(y, saw_pad([midi(n) for n in ch], 4.4, 1400, 0.003) * env(int(4.4 * SR), 0.9, 3.2, 0.7) * 0.5, s)
        for j, n in enumerate([ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[3] + 12, ch[2] + 12, ch[1] + 12, ch[2] + 12, ch[3] + 12]):
            place(y, piano(midi(n), 2.0, 0.3), s + j * 0.5)
        s += 4.0
        i += 1
    return y


def sinister(d, bpm=96):
    y = saw_pad([midi(33)], d, 250) * 0.6
    beat = 60 / bpm
    mel = [69, 72, 76, 75, 72, 69, 68, 71, 74, 72, 68, 64, 69, 72, 76, 81, 80, 76, 75, 72, 69, 68, 69, None]
    s, k = 0.0, 0
    while s < d:
        n = mel[k % len(mel)]
        if n:
            place(y, bell(midi(n), 2.0, 0.22), s)
        if k % 3 == 0:
            place(y, piano(midi(45 if (k // 12) % 2 == 0 else 44), 2.0, 0.25), s)
        s += beat
        k += 1
    return y


MOODS = dict(tension=tension, warm=warm, action=action, emotional=emotional, sinister=sinister)


def score(segments, total):
    """segments: [(start, end, mood)] → pista estéreo con fundidos entre ánimos."""
    out = np.zeros((int(total * SR) + SR, 2))
    for start, end, mood in segments:
        if mood not in MOODS or end - start < 0.2:
            continue
        d = end - start + 1.5
        x = MOODS[mood](d)
        n = len(x)
        fade = np.ones(n)
        fi, fo = int(1.0 * SR), int(1.5 * SR)
        fade[:fi] = np.linspace(0, 1, fi)
        fade[-fo:] = np.linspace(1, 0, fo)
        x = reverb(x * fade, 2.2, 0.3)
        s = int(max(0, start - 0.5) * SR)
        e = min(len(out), s + len(x))
        out[s:e] += x[: e - s]
    p = np.abs(out).max() + 1e-9
    return out / p * 10 ** (-14 / 20)
