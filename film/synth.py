"""Small numpy/scipy synth toolkit: additive pads, mallets, bells, noise FX, thunder, reverb."""
import numpy as np
from scipy import signal

SR = 48000
_rng = np.random.RandomState(1234)


def midi(m):
    return 440.0 * 2.0 ** ((np.asarray(m, float) - 69.0) / 12.0)


NOTE = {}
for _i, _n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]):
    for _o in range(0, 9):
        NOTE[f"{_n}{_o}"] = 12 * (_o + 1) + _i


def hz(name):
    return float(midi(NOTE[name]))


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def pan_gains(p):
    a = (np.clip(p, -1, 1) + 1.0) * np.pi / 4.0
    return np.cos(a), np.sin(a)


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


class Mixer:
    def __init__(self, total):
        self.n = int(total * SR) + SR
        self.dry = np.zeros((2, self.n), np.float32)
        self.rev = np.zeros((2, self.n), np.float32)    # long hall send
        self.pla = np.zeros((2, self.n), np.float32)    # short plate send

    def add(self, sig, t0, gain=1.0, pan=0.0, send=0.25, plate=0.0):
        """sig: mono (n,) or stereo (2,n)"""
        sig = np.asarray(sig, np.float32)
        if sig.ndim == 1:
            gl, gr = pan_gains(pan)
            st = np.stack([sig * gl, sig * gr])
        else:
            st = sig
        i0 = int(round(t0 * SR))
        n = st.shape[1]
        a0 = max(i0, 0)
        a1 = min(i0 + n, self.n)
        if a1 <= a0:
            return
        seg = st[:, a0 - i0:a1 - i0] * gain
        self.dry[:, a0:a1] += seg
        if send > 0:
            self.rev[:, a0:a1] += seg * send
        if plate > 0:
            self.pla[:, a0:a1] += seg * plate


# ------------------------------------------------------------------ filters
def butter_sos(kind, f, order=2):
    return signal.butter(order, f, btype=kind, fs=SR, output="sos")


def lp(x, f, order=2):
    return signal.sosfilt(butter_sos("lowpass", min(f, SR / 2 - 100), order), x)


def hp(x, f, order=2):
    return signal.sosfilt(butter_sos("highpass", f, order), x)


def bp(x, f1, f2, order=2):
    return signal.sosfilt(butter_sos("bandpass", [f1, min(f2, SR / 2 - 100)], order), x)


def tv_filter(x, curve, kind="lowpass", q_width=None, blk=1024, order=2):
    """block-wise time-varying filter. curve = cutoff (Hz) per sample (or bandpass centre with q_width ratio)."""
    out = np.zeros_like(x)
    zi = None
    for b in range(0, len(x), blk):
        fc = float(np.clip(curve[min(b + blk // 2, len(curve) - 1)], 25, SR / 2 - 200))
        if kind == "bandpass":
            w = q_width or 0.5
            sos = signal.butter(order, [max(fc * (1 - w), 20), min(fc * (1 + w), SR / 2 - 100)], btype="bandpass", fs=SR, output="sos")
        else:
            sos = signal.butter(order, fc, btype=kind, fs=SR, output="sos")
        if zi is None or zi.shape[0] != sos.shape[0]:
            zi = np.zeros((sos.shape[0], 2))
        y, zi = signal.sosfilt(sos, x[b:b + blk], zi=zi)
        out[b:b + blk] = y
    return out


def white(n):
    return _rng.randn(n).astype(np.float64)


def pink(n):
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    return signal.lfilter(b, a, white(n)) * 5.0


def brown(n):
    x = np.cumsum(white(n))
    x = hp(x, 20)
    return x / (np.std(x) + 1e-9)


# ------------------------------------------------------------------ voices
def pad_note(f, dur, a=1.4, r=2.0, bright=2200.0, detune=(-8, 0, 7), spread=0.7, vib=0.0, tilt=1.0, seed=0):
    rng = np.random.RandomState(seed + int(f * 10) % 1000)
    n = int((dur + r) * SR)
    t = np.arange(n) / SR
    out = np.zeros((2, n))
    for i, dc in enumerate(detune):
        ff = f * 2 ** (dc / 1200.0)
        ph0 = rng.rand() * 6.283
        lfo = vib * np.sin(2 * np.pi * (0.35 + 0.11 * i) * t + ph0) if vib else 0.0
        theta = 2 * np.pi * ff * t + lfo
        sig = np.zeros(n)
        K = int(min(36, (SR / 2.2) / ff))
        for k in range(1, K + 1):
            amp = k ** (-tilt) * np.exp(-((k * ff) / bright) ** 2)
            if amp < 1e-4:
                continue
            sig += amp * np.sin(k * theta + ph0 * k)
        p = (i - (len(detune) - 1) / 2) / max((len(detune) - 1) / 2, 1) * spread
        gl, gr = pan_gains(p)
        out[0] += sig * gl
        out[1] += sig * gr
    env = np.ones(n)
    na = int(a * SR)
    env[:na] = smoothstep(np.arange(na) / max(na, 1)) ** 1.2
    nr = int(r * SR)
    env[-nr:] *= 1 - smoothstep(np.arange(nr) / max(nr, 1))
    return out * env / len(detune) * 0.6


def sine_bass(f, dur, a=0.05, r=0.8, harm=0.25, hold_decay=None):
    n = int((dur + r) * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + (harm + 0.35) * np.sin(4 * np.pi * f * t) * 0.6 + 0.12 * np.sin(6 * np.pi * f * t)
    env = np.ones(n)
    na = max(int(a * SR), 1)
    env[:na] = np.linspace(0, 1, na) ** 1.5
    nr = int(r * SR)
    env[-nr:] *= np.linspace(1, 0, nr) ** 1.5
    if hold_decay:
        env *= np.exp(-t / hold_decay)
    return sig * env


def pluck(f, dur=1.6, vel=1.0, bright=1.0, decay=0.9, seed=0):
    """soft mallet / electric-piano-ish tone."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    ratios = np.array([1, 2, 3, 4, 5, 6, 7, 9], float)
    amps = np.array([1.0, 0.50, 0.30, 0.20, 0.11, 0.07, 0.045, 0.025]) * np.array([1, bright, bright ** 1.5, bright ** 2, bright ** 2, bright ** 2, bright ** 2, bright ** 2])
    sig = np.zeros(n)
    for k, (rt, am) in enumerate(zip(ratios, amps)):
        if f * rt > 14000:
            continue
        tau = decay / (1 + 0.7 * k)
        sig += am * np.exp(-t / tau) * np.sin(2 * np.pi * f * rt * t + 0.3 * k)
    # hammer
    ht = np.exp(-t / 0.004) * np.random.RandomState(seed).randn(n) * 0.06 * vel
    sig = sig * vel + bp(ht, 800, 5000)
    na = int(0.0025 * SR)
    sig[:na] *= np.linspace(0, 1, na)
    return sig * np.exp(-np.maximum(t - (dur - 0.25), 0) / 0.08)


def bell(f, dur=3.0, vel=1.0, decay=1.0, bright=1.0, seed=0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ratios = np.array([1.0, 2.0, 2.756, 4.07, 5.4, 8.93])
    amps = np.array([1.0, 0.55, 0.45, 0.25, 0.16, 0.07]) * np.array([1, 1, bright, bright, bright ** 2, bright ** 2])
    taus = np.array([1.0, 0.75, 0.6, 0.42, 0.30, 0.18]) * decay
    sig = np.zeros(n)
    for rt, am, tau in zip(ratios, amps, taus):
        if f * rt > 15000:
            continue
        sig += am * np.exp(-t / tau) * np.sin(2 * np.pi * f * rt * t + 0.5 * rt)
        sig += 0.3 * am * np.exp(-t / tau) * np.sin(2 * np.pi * f * rt * 1.0035 * t)
    na = int(0.002 * SR)
    sig[:na] *= np.linspace(0, 1, na)
    return sig * vel * np.exp(-np.maximum(t - (dur - 0.3), 0) / 0.1) * 0.5


def tick(f=2400, vel=1.0, dur=0.12):
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = hp(white(n), 1800) * np.exp(-t / 0.006)
    ping = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.03)
    return (nz * 0.6 + ping * 0.8) * vel


def boom(dur=3.0, f0=110.0, f1=32.0, vel=1.0, tail=1.6):
    f1 = max(f1, 42.0)
    vel = vel * 0.62
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.12)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sig = np.sin(ph) * np.exp(-t / tail)
    sub = np.sin(2 * np.pi * f1 * t) * np.exp(-t / (tail * 1.4)) * 0.6
    nz = lp(white(n), 400) * np.exp(-t / 0.35) * 0.7 + hp(white(n), 3000) * np.exp(-t / 0.05) * 0.2
    return (sig + sub + nz) * vel


def whoosh(dur, f_start, f_end, vel=1.0, width=0.7, shape=2.0, rise=True, tone=None):
    n = int(dur * SR)
    x = np.linspace(0, 1, n)
    curve = f_start * (f_end / f_start) ** x
    sig = tv_filter(white(n), curve, "bandpass", width)
    env = x ** shape if rise else (1 - x) ** shape
    env = env * np.minimum(1, (1 - x) * 40) if rise else env * np.minimum(1, x * 60)
    out = sig * env
    out = out / (np.std(out) + 1e-9) * 0.25
    return out * vel


def glide_sine(dur, f0, f1, vel=1.0, shape=2.0, harm=0.0):
    n = int(dur * SR)
    x = np.linspace(0, 1, n)
    f = f0 * (f1 / f0) ** (x ** shape)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sig = np.sin(ph) + harm * np.sin(2 * ph)
    return sig * (x ** 1.6) * np.minimum(1, (1 - x) * 30) * vel


def crack(vel=1.0):
    n = int(2.4 * SR)
    t = np.arange(n) / SR
    a = hp(white(n), 1200) * np.exp(-t / 0.05)
    b = bp(white(n), 300, 3500) * np.exp(-t / 0.28) * 0.7
    c = lp(white(n), 160) * np.exp(-t / 0.9) * 1.2
    th = np.sin(2 * np.pi * 52 * t) * np.exp(-t / 0.5)
    return (a * 0.9 + b + c + th * 0.5) * vel


def thunder(dur=6.0, vel=1.0, seed=3):
    rng = np.random.RandomState(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = rng.randn(n)
    low = lp(nz, 110, 3)
    mid = lp(nz, 520, 2) - lp(nz, 120, 2)
    hi = bp(nz, 800, 3500) * 0.25
    env = np.zeros(n)
    # crack front then a rolling train of bursts
    env += np.exp(-t / 0.22) * 1.0
    for _ in range(11):
        ti = rng.uniform(0.15, dur * 0.55)
        am = rng.uniform(0.25, 0.85) * np.exp(-ti / 3.0)
        tau = rng.uniform(0.5, 1.4)
        x = np.maximum(t - ti, 0)
        env += am * (1 - np.exp(-x / 0.12)) * np.exp(-x / tau) * (t >= ti)
    env *= np.exp(-t / 3.6) * np.minimum(1, t / 0.004 + 0.0)
    cur = 700 * np.exp(-t / 1.8) + 90
    shaped = tv_filter(nz, cur, "lowpass", blk=2048, order=2)
    sub = np.sin(2 * np.pi * (34 + 12 * np.exp(-t / 0.9)) * t) * np.exp(-t / 1.7) * 0.9
    sig = low * env * 3.0 + mid * env * 0.9 + shaped * env * 0.5 + hi * np.exp(-t / 0.5) * env + sub
    return sig / (np.max(np.abs(sig)) + 1e-9) * vel


def make_ir(dur=3.8, seed=1, pre=0.018, damp=5200.0, rt_hf=0.55):
    rng = np.random.RandomState(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((2, n))
    for ch in range(2):
        nz = rng.randn(n)
        lo = lp(nz, 900, 2) * np.exp(-t * 6.9 / dur)
        hi_ = lp(nz, damp, 2) * np.exp(-t * 6.9 / (dur * rt_hf))
        x = lo * 0.7 + hi_ * 0.5
        # early reflections
        for _ in range(14):
            d = int((pre + rng.uniform(0.0, 0.09)) * SR)
            if d < n:
                x[d] += rng.choice([-1, 1]) * rng.uniform(0.3, 1.0) * 6
        k = int(pre * SR)
        x[:k] = 0
        x *= np.minimum(1, t / 0.03)
        out[ch] = x
    out /= np.sqrt(np.sum(out ** 2, axis=1, keepdims=True)) + 1e-9
    return out


def convolve(x, ir):
    """x: (2,n) stereo, ir: (2,m)"""
    out = np.zeros_like(x, dtype=np.float32)
    for ch in range(2):
        out[ch] = signal.fftconvolve(x[ch].astype(np.float64), ir[ch], mode="full")[:x.shape[1]].astype(np.float32)
    return out
