"""LATE LIGHT - score + sound design. Every cue is derived from timeline.py / neuro.py so picture and sound stay locked."""
import sys, os
import numpy as np
from scipy.io import wavfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import *
import synth as sy
from synth import SR, hz, midi, NOTE

rng = np.random.RandomState(99)
M = sy.Mixer(TOTAL)


def G(name, local):
    for s in SCENES:
        if s["name"] == name:
            return s["t0"] + local
    raise KeyError(name)


def bar(b):
    return b * BAR


def n_(name):
    return hz(name)


PENT = ["D", "E", "F#", "A", "B"]


def pent(oct_, idx):
    """idx-th note of D major pentatonic starting at D<oct_>"""
    names = PENT
    o = oct_ + idx // 5
    nm = names[idx % 5]
    # B sits above A within the same octave numbering; D(o) E(o) F#(o) A(o) B(o)
    return hz(f"{nm}{o}")


def chord_pad(notes, t0, dur, gain=0.5, a=1.6, r=2.2, bright=2000, vib=0.0, send=0.35, tilt=1.1, spread=0.8):
    for i, nm in enumerate(notes):
        f = n_(nm)
        p = pad_pan(i, len(notes))
        sig = sy.pad_note(f, dur, a=a, r=r, bright=bright, vib=vib, tilt=tilt, spread=spread, seed=i)
        M.add(sig, t0, gain=gain / np.sqrt(len(notes)), send=send, plate=0.05)


def pad_pan(i, n):
    return 0.0


def text_tick(t0, f=None, vel=0.18):
    """soft glassy accent where a line of text lands"""
    f = f or n_("A5")
    M.add(sy.bell(f, 2.4, vel, 0.8, 0.8), t0, gain=1.0, pan=rng.uniform(-0.3, 0.3), send=0.5, plate=0.1)
    air = sy.whoosh(0.5, 2500, 7000, 1.0, 0.6, 2.0, rise=True) * 0.25
    M.add(air, t0 - 0.35, gain=0.4, send=0.3)


# =====================================================================  S1  STARS
def s1():
    t0 = SCENES[0]["t0"]
    # deep drone
    for f, g in ((n_("D1"), 0.5), (n_("A1"), 0.28), (n_("D2"), 0.2)):
        sig = sy.sine_bass(f, 10.0, a=3.0, r=1.5, harm=0.2)
        M.add(sig, 0.0, gain=g, send=0.2)
    # pad: Bm9 | Bm9 | Gmaj7 | Asus
    chord_pad(["B2", "F#3", "A3", "C#4", "D4"], 0.6, 5.2, gain=0.55, a=2.6, r=2.0, bright=1500, vib=0.0)
    chord_pad(["G2", "D3", "F#3", "B3", "D4"], bar(2) - 0.2, BAR + 0.4, gain=0.55, a=1.8, r=2.0, bright=1900)
    chord_pad(["A2", "E3", "A3", "D4", "E4"], bar(3) - 0.2, BAR + 0.5, gain=0.55, a=1.6, r=1.2, bright=2800)
    # HUD sparkles
    cols = ["D6", "A5", "F#6", "E6", "B5"]
    for i in range(1, 6):
        ts = 1.5 + 0.42 * (i - 1) + 0.55
        M.add(sy.bell(n_(cols[i - 1]), 3.2, 0.20, 1.0, 0.9), ts, pan=(-0.7 + 0.35 * i) * 0.8, send=0.55, plate=0.15)
    M.add(sy.bell(n_("A4"), 4.0, 0.22, 1.4, 0.7), 3.35 + 0.6, pan=0.4, send=0.6)
    text_tick(2.3 + 0.35, n_("D6"), 0.12)
    text_tick(3.2 + 0.35, n_("A5"), 0.12)
    # swelling of the doomed star: riser 4.9 -> 5.9
    d = S1_DEATH
    M.add(sy.glide_sine(1.05, n_("D3"), n_("D5"), 0.18, 2.5, harm=0.25), d - 1.05, send=0.5)
    M.add(sy.whoosh(1.05, 500, 7000, 1.0, 0.8, 2.2, True), d - 1.05, gain=0.55, send=0.4)
    # supernova
    M.add(sy.boom(4.0, 130, 30, 1.0, 1.9), d, gain=0.95, send=0.25)
    M.add(sy.whoosh(0.9, 9000, 500, 1.0, 0.9, 1.3, False), d, gain=0.5, send=0.5)
    for k in range(9):   # spray of glass
        f = pent(5, k % 5 + (k // 5) * 5)
        M.add(sy.bell(f * (2 if k > 5 else 1), 3.0, 0.20 * (1 - k * 0.07), 0.9, 1.0), d + 0.05 + k * 0.085, pan=rng.uniform(-0.8, 0.8), send=0.6)
    # the hollow after: dissonant ghost
    for nm, g in (("D3", 0.3), ("A3", 0.2)):
        M.add(sy.pad_note(n_(nm), 3.0, a=0.2, r=3.0, bright=900, tilt=1.6), d + 0.1, gain=g, send=0.5)
    # glints as the front crosses stars
    p0 = np.array(HEROES[0]["p"])
    order = [5, 2, 1, 4, 3]
    for j, i in enumerate(range(1, len(HEROES))):
        pi = np.array(HEROES[i]["p"])
        d_ = np.linalg.norm(pi - p0)
        # find t where R(t) = d_*scale
        lo, hi = d, d + S1_RING_DUR
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            R = 0.012 + 1.62 * ((mid - d) / S1_RING_DUR) ** 2.1
            if R < d_ * s1_scale(mid):
                lo = mid
            else:
                hi = mid
        tg = 0.5 * (lo + hi)
        f = pent(6, [0, 2, 1, 3, 4][j % 5])
        M.add(sy.bell(f * (1 if f < 1900 else 1), 3.4, 0.26, 1.0, 1.0), tg, pan=np.clip(pi[0] * 1.2, -0.9, 0.9), send=0.55, plate=0.1)
    # the arriving light: swell 6.2 -> 10.67
    dur = 10.667 - 6.2
    sw = sy.whoosh(dur, 300, 9000, 1.0, 1.1, 2.6, True) * 0.7
    M.add(sw, 6.2, gain=0.55, send=0.5)
    # rising saw cluster (pitch climbing, accelerating tremolo)
    n = int(dur * SR)
    x = np.linspace(0, 1, n)
    f_c = n_("D3") * (4.0 ** (x ** 1.8))
    sig = np.zeros(n)
    for dc, pn in ((-9, 0), (0, 0), (9, 0), (1200 - 4, 0)):
        ph = 2 * np.pi * np.cumsum(f_c * 2 ** (dc / 1200)) / SR
        sig += np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * np.cumsum(2.0 + 14.0 * x ** 2) / SR)
    sig = sig * trem * (x ** 2.4) * 0.12
    M.add(sig, 6.2, gain=0.8, send=0.4)
    # arrival impact on the downbeat of S2
    return


# =====================================================================  S2  SUN
def s2():
    T = SCENES[1]["t0"]
    # downbeat: white-out resolves
    M.add(sy.boom(5.0, 100, 36, 1.0, 2.6), T, gain=0.9, send=0.3)
    for k, nm in enumerate(["D4", "A4", "F#5", "C#6", "E6", "A5"]):
        M.add(sy.bell(n_(nm), 5.0, 0.28, 1.4, 0.9), T + 0.02 + k * 0.045, pan=(-0.6 + 0.25 * k) * 0.8, send=0.65, plate=0.1)
    M.add(sy.whoosh(2.6, 9000, 300, 1.0, 1.0, 1.0, False), T, gain=0.45, send=0.5)
    # bass pedal D
    M.add(sy.sine_bass(n_("D1"), 9.0, a=0.6, r=1.6, harm=0.3), T, gain=0.65, send=0.15)
    M.add(sy.sine_bass(n_("D2"), 8.0, a=1.0, r=1.4), T + 0.5, gain=0.25, send=0.2)
    # pad progression  Dmaj9 | A/C# | Bm7 | Gmaj9
    chord_pad(["D3", "A3", "E4", "F#4", "C#5"], bar(4), BAR + 0.4, gain=0.62, a=0.7, r=2.0, bright=3600, vib=0.0007)
    chord_pad(["C#3", "A3", "E4", "A4", "C#5"], bar(5) - 0.1, BAR + 0.5, gain=0.55, a=1.0, r=2.0, bright=3200, vib=0.0007)
    chord_pad(["B2", "F#3", "A3", "D4", "F#4"], bar(6) - 0.1, BAR + 0.5, gain=0.55, a=1.0, r=2.0, bright=3000, vib=0.0007)
    chord_pad(["G2", "D3", "A3", "B3", "F#4"], bar(7) - 0.1, BAR + 1.6, gain=0.62, a=1.0, r=3.0, bright=3800, vib=0.0008)
    # gentle arp (8ths) after the swell settles
    chords = [["D4", "F#4", "A4", "E5"], ["C#4", "E4", "A4", "C#5"], ["B3", "D4", "F#4", "A4"], ["G3", "B3", "D4", "F#4"]]
    pattern = [0, 1, 2, 3, 2, 1, 3, 2]
    for bi in range(4):
        for k in range(8):
            tt_ = bar(4 + bi) + k * (BEAT / 2)
            if tt_ < T + 1.6:
                continue
            nm = chords[bi][pattern[k]]
            vel = 0.20 * (0.8 + 0.2 * (k % 4 == 0)) * smoothstep_(tt_ - (T + 1.6), 1.5)
            M.add(sy.pluck(n_(nm) * (2 if k % 8 == 5 else 1), 1.6, vel, 0.9, 0.9), tt_, pan=-0.25 + 0.5 * (k % 4) / 3, send=0.45, plate=0.15)
    # photon launch
    M.add(sy.glide_sine(0.7, n_("A4"), n_("A6"), 0.14, 1.5), G("sun", S2_LAUNCH) - 0.55, send=0.5)
    M.add(sy.whoosh(0.7, 800, 6000, 1.0, 0.7, 2.0, True), G("sun", S2_LAUNCH) - 0.65, gain=0.3, send=0.4)
    # minute ticks, pitch climbing D major pentatonic
    for k in range(8):
        f = 60.0 * (k + 1) / S2_TOTAL_SEC
        tk = G("sun", S2_LAUNCH + f * (S2_ARRIVE - S2_LAUNCH))
        note = pent(5, k)
        M.add(sy.bell(note, 1.6, 0.18 + 0.01 * k, 0.28, 0.7), tk, pan=-0.5 + k * 0.1, send=0.5, plate=0.2)
        M.add(sy.tick(1800 + 120 * k, 0.5), tk, gain=0.45, pan=-0.5 + k * 0.1, send=0.2, plate=0.2)
        M.add(sy.boom(0.5, 120, 70, 0.20, 0.12), tk, gain=1.0, send=0.05)
    # text
    text_tick(G("sun", 2.2 + 0.4), n_("F#5"), 0.12)
    text_tick(G("sun", 3.0 + 0.4), n_("D6"), 0.14)
    text_tick(G("sun", 3.55 + 0.4), n_("A5"), 0.10)
    # earth lit
    ta = G("sun", S2_ARRIVE)
    M.add(sy.boom(3.5, 90, 40, 1.0, 1.8), ta, gain=0.55, send=0.3)
    for k, nm in enumerate(["D5", "F#5", "A5", "D6", "F#6", "A6"]):
        M.add(sy.bell(n_(nm), 5.0, 0.30, 1.5, 0.9), ta + 0.03 * k, pan=-0.6 + 0.24 * k, send=0.7, plate=0.1)
    M.add(sy.whoosh(2.0, 6000, 700, 1.0, 0.9, 1.0, False), ta, gain=0.35, send=0.5)
    # fade of the sun into night: drone remains (handled by envelope on S2 elements via master gain curve)


def smoothstep_(x, d):
    return float(np.clip(x / d, 0, 1) ** 2 * (3 - 2 * np.clip(x / d, 0, 1)))


# =====================================================================  S3  STORM
def s3():
    T = SCENES[2]["t0"]
    L = SCENES[2]["t1"] - T
    # rain bed + wind
    n = int((L + 1.4) * SR)
    x = np.linspace(0, 1, n)
    rain = sy.bp(sy.pink(n), 1800, 9500) * 0.5
    rain *= np.minimum(1, x * (L + 1.4) / 1.5) * (1 - sy.smoothstep((x * (L + 1.4) - (L + 0.3)) / 1.0))
    st = np.stack([rain, np.roll(rain, 733)])
    M.add(st, T - 1.2, gain=0.20, send=0.2)
    wind = sy.tv_filter(sy.white(n), 260 + 120 * np.sin(2 * np.pi * x * 3.0), "bandpass", 0.5) * 0.9
    wind *= 0.6 + 0.4 * np.sin(2 * np.pi * x * 2.2 + 1.0)
    wind *= np.minimum(1, x * (L + 1.4) / 2.0) * (1 - sy.smoothstep((x * (L + 1.4) - (L + 0.4)) / 0.8))
    M.add(wind, T - 1.2, gain=0.16, pan=0.0, send=0.3)
    # dark drone Bm
    M.add(sy.sine_bass(n_("B1"), L + 1.0, a=1.2, r=1.2, harm=0.5), T - 0.6, gain=0.55, send=0.2)
    M.add(sy.sine_bass(n_("F#2"), L + 0.4, a=2.0, r=1.2, harm=0.4), T - 0.3, gain=0.26, send=0.2)
    chord_pad(["B2", "D3", "F#3", "C4"], T - 0.2, 5.4, gain=0.34, a=2.2, r=1.8, bright=900, tilt=1.4, spread=0.9)
    chord_pad(["E2", "B2", "G3", "D4", "F#4"], T + 5.2, 3.2, gain=0.38, a=0.8, r=1.2, bright=1200, tilt=1.3)
    # precursor sheet flashes (distant)
    M.add(sy.thunder(4.0, 0.22, 21), T + 1.15, gain=0.6, send=0.35)
    M.add(sy.thunder(3.0, 0.12, 22), T + 1.65, gain=0.5, send=0.35)
    # tension riser: strike -> thunder
    ts = T + S3_STRIKE
    th = ts + S3_DELAY
    M.add(sy.glide_sine(S3_DELAY, n_("B2"), n_("B4"), 0.12, 2.2, harm=0.3), ts + 0.2, gain=1.0, send=0.5)
    # lightning
    M.add(sy.glide_sine(0.13, 900, 5000, 0.18, 1.2), ts - 0.13, send=0.3)
    M.add(sy.crack(1.0), ts, gain=0.95, send=0.22, plate=0.1)
    M.add(sy.crack(0.55), ts + 0.10, gain=0.6, send=0.22)
    M.add(sy.crack(0.35), ts + 0.21, gain=0.45, send=0.22)
    # ear ring
    n2 = int(1.4 * SR)
    tt_ = np.arange(n2) / SR
    ring = np.sin(2 * np.pi * 7400 * tt_) * np.exp(-tt_ / 0.5) * 0.04
    M.add(ring, ts + 0.05, pan=0.0, send=0.1)
    # slow sonar-like pulses marking the sound wave moving
    for k in range(1, 4):
        M.add(sy.bell(n_("B3") * (1 if k < 3 else 1.5), 2.5, 0.06, 0.5, 0.3), ts + k * 0.75, pan=0.3, send=0.7)
    # THUNDER arrival (+ the visual shake)
    M.add(sy.thunder(7.0, 1.0, 5), th, gain=1.0, send=0.18, plate=0.05)
    M.add(sy.boom(3.0, 70, 30, 1.0, 1.7), th, gain=0.8, send=0.1)
    # distant answering rumble
    M.add(sy.thunder(3.5, 0.28, 8), T + 5.55, gain=0.7, send=0.35)
    # text
    text_tick(T + 2.35 + 0.4, n_("D5"), 0.09)
    text_tick(T + 3.3 + 0.4, n_("F#5"), 0.09)
    # closing flash + hit  (cut to neurons)
    tc = T + 7.5
    M.add(sy.whoosh(0.7, 400, 9000, 1.0, 1.0, 2.5, True), tc - 0.05, gain=0.7, send=0.3)
    M.add(sy.crack(0.9), tc + 0.35, gain=0.85, send=0.22)
    M.add(sy.boom(2.0, 100, 38, 1.0, 1.0), tc + 0.35, gain=0.7, send=0.2)


# =====================================================================  S4  NEURO
def s4():
    import neuro
    T = SCENES[3]["t0"]
    arr = neuro.arrival_time()
    # airy bed
    chord_pad(["G3", "D4", "F#4", "B4", "A4"], T + 0.1, 5.0, gain=0.34, a=2.0, r=1.5, bright=4200, tilt=0.9, vib=0.0012)
    chord_pad(["E3", "B3", "G4", "D5", "F#5"], T + 3.2, 3.0, gain=0.34, a=1.6, r=1.2, bright=4500, tilt=0.9, vib=0.0012)
    M.add(sy.sine_bass(n_("G1"), 5.0, a=2.0, r=1.0, harm=0.2), T + 0.2, gain=0.35, send=0.15)
    M.add(sy.sine_bass(n_("E1"), 3.0, a=0.5, r=1.0, harm=0.2), T + 3.3, gain=0.3, send=0.15)
    # touch spark
    t_touch = T + S4_T0
    M.add(sy.whoosh(0.5, 1500, 9000, 1.0, 0.6, 1.6, True), t_touch - 0.45, gain=0.35, send=0.4)
    for k, nm in enumerate(["D6", "A6", "F#6"]):
        M.add(sy.bell(n_(nm), 3.0, 0.20, 0.9, 1.0), t_touch + 0.015 * k, pan=0.6, send=0.5)
    # bead ticks climbing the pentatonic
    bt = neuro.bead_times()
    for i, tb in enumerate(bt):
        idx = int(i * 0.55)
        f = pent(4, idx % 12 if False else min(idx, 14))
        vel = 0.11 + 0.10 * (i / len(bt))
        pan = 0.65 - 1.3 * (i / len(bt))
        M.add(sy.tick(2600 + 90 * i, 0.55), T + tb, gain=0.5, pan=pan, send=0.15, plate=0.25)
        M.add(sy.pluck(f * 2, 0.9, vel, 1.2, 0.35), T + tb, pan=pan, send=0.45, plate=0.15)
    # ignition cascade
    ta = T + arr
    M.add(sy.whoosh(0.8, 400, 8000, 1.0, 0.9, 2.2, True), ta - 0.8, gain=0.45, send=0.4)
    M.add(sy.boom(3.5, 90, 36, 1.0, 1.8), ta, gain=0.7, send=0.25)
    chord_pad(["D3", "A3", "F#4", "C#5", "E5"], ta + 0.05, 4.2, gain=0.62, a=0.5, r=1.8, bright=3800)
    M.add(sy.sine_bass(n_("D1"), 4.0, a=0.1, r=1.2, harm=0.3), ta, gain=0.8, send=0.2)
    n_notes = 34
    for k in range(n_notes):
        tk = ta + 0.02 + k * (0.048 + 0.0022 * k)
        idx = int(rng.uniform(2, 14))
        f = pent(5, idx)
        vel = 0.24 * np.exp(-k / 28.0)
        M.add(sy.bell(f, 2.6, vel, 0.8, 1.0), tk, pan=rng.uniform(-0.9, 0.9), send=0.6, plate=0.1)
    # text
    text_tick(T + 2.3 + 0.4, n_("F#5"), 0.09)
    text_tick(T + 3.15 + 0.4, n_("A5"), 0.09)
    # riser to white
    tr = T + 7.0
    M.add(sy.whoosh(1.5, 300, 9500, 1.0, 1.1, 2.6, True), tr - 0.1, gain=0.65, send=0.35)
    M.add(sy.glide_sine(1.5, n_("D4"), n_("D6"), 0.14, 2.2, harm=0.2), tr - 0.1, send=0.5)


# =====================================================================  S5  PAPER
def s5():
    T = SCENES[4]["t0"]
    # white resolves: soft impact + warm bed
    M.add(sy.boom(3.0, 85, 38, 1.0, 1.4), T, gain=0.45, send=0.2)
    M.add(sy.whoosh(1.6, 9000, 600, 1.0, 1.0, 1.2, False), T, gain=0.28, send=0.4)
    chord_pad(["D3", "A3", "D4", "F#4", "E5"], T, BAR + 0.2, gain=0.5, a=0.4, r=1.5, bright=3400)
    chord_pad(["C#3", "A3", "E4", "A4", "C#5"], T + BAR - 0.1, BAR + 0.2, gain=0.5, a=0.8, r=1.5, bright=3400)
    chord_pad(["B2", "F#3", "A3", "D4", "F#4"], T + 2 * BAR - 0.1, BAR + 0.6, gain=0.52, a=0.8, r=2.0, bright=3300)
    M.add(sy.sine_bass(n_("D1"), 2.8, a=0.2, r=0.6), T, gain=0.55, send=0.1)
    M.add(sy.sine_bass(n_("A1"), 2.8, a=0.2, r=0.6), T + BAR - 0.05, gain=0.5, send=0.1)
    M.add(sy.sine_bass(n_("B1"), 2.8, a=0.2, r=0.8), T + 2 * BAR - 0.05, gain=0.5, send=0.1)
    # marimba arp, 8ths, bright and clean
    chords = [["D4", "F#4", "A4", "E5"], ["C#4", "E4", "A4", "C#5"], ["B3", "D4", "F#4", "A4"]]
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    for bi in range(3):
        for k in range(8):
            tk = T + bi * BAR + k * (BEAT / 2)
            if tk < T + 0.6:
                continue
            nm = chords[bi][pat[k]]
            M.add(sy.pluck(n_(nm) * 2, 1.0, 0.20 * (1.0 if k % 2 == 0 else 0.75), 1.15, 0.5), tk, pan=-0.4 + 0.8 * (k % 4) / 3, send=0.35, plate=0.2)
    # soft pulse
    for k in range(int(3 * BAR / BEAT)):
        tk = T + k * BEAT
        if tk < T + 0.7:
            continue
        M.add(sy.boom(0.7, 80, 46, 0.35, 0.22), tk, gain=0.5, send=0.08)
        if k % 2 == 1:
            M.add(sy.tick(5200, 0.18), tk, gain=0.4, pan=0.3, send=0.2, plate=0.3)
    # inbound sweeps (four streams)
    for i, (phi0, d, turns, t0s, t1s, lab) in enumerate(S5_STREAMS):
        M.add(sy.whoosh(t1s - t0s + 0.2, 6000 * (1 - 0.1 * i), 700 + 120 * i, 1.0, 0.8, 0.8, False), T + t0s - 0.05, gain=0.12, pan=[-0.5, 0.5, -0.2, 0.2][i], send=0.35)
    # arrivals: build a D major chord
    arr_notes = ["D5", "F#5", "A5", "D6"]
    for i, (phi0, d, turns, t0s, t1s, lab) in enumerate(S5_STREAMS):
        ta = T + t1s
        M.add(sy.bell(n_(arr_notes[i]), 3.0 + i, 0.30 + 0.05 * i, 0.9 + 0.2 * i, 1.0), ta, pan=[-0.4, 0.4, -0.15, 0.15][i], send=0.55, plate=0.1)
        M.add(sy.bell(n_(arr_notes[i]) * 2, 2.0, 0.12, 0.5, 1.0), ta + 0.01, pan=0.0, send=0.5)
        M.add(sy.boom(1.6, 100 - 12 * i, 44 - 2 * i, 0.5 + 0.1 * i, 0.5 + 0.15 * i), ta, gain=0.6, send=0.15)
    # final arrival adds weight
    t4 = T + S5_STREAMS[3][4]
    M.add(sy.boom(4.0, 90, 36, 1.0, 2.2), t4, gain=0.7, send=0.3)
    M.add(sy.whoosh(2.0, 8000, 600, 1.0, 1.0, 1.0, False), t4, gain=0.25, send=0.5)
    # text accents
    text_tick(T + 0.9 + 0.3, n_("D5"), 0.10)
    text_tick(T + 1.35 + 0.3, n_("F#5"), 0.10)
    tl = T + 5.25
    M.add(sy.bell(n_("D3"), 3.5, 0.28, 1.5, 0.5), tl, send=0.4)
    text_tick(tl + 0.25, n_("A5"), 0.12)
    # gold ignition -> iris
    tg = T + S5_GOLD_T
    M.add(sy.glide_sine(1.7, n_("D4"), n_("D6"), 0.16, 2.0, harm=0.3), tg, send=0.5)
    M.add(sy.whoosh(1.9, 300, 10000, 1.0, 1.2, 2.2, True), tg - 0.1, gain=0.7, send=0.35)


# =====================================================================  S6  REACH
def s6():
    T = SCENES[5]["t0"]
    # downbeat: iris opens into dusk
    M.add(sy.boom(5.0, 95, 34, 1.0, 2.6), T - 0.25, gain=0.8, send=0.3)
    M.add(sy.whoosh(1.8, 9000, 400, 1.0, 1.0, 1.0, False), T - 0.1, gain=0.35, send=0.5)
    # pad progression  Gmaj9 | D/F# | Bm9 | Gmaj7->A | Dmaj9
    ch = [(["G2", "D3", "A3", "B3", "F#4"], 0.60),
          (["F#2", "A2", "D3", "A3", "D4", "F#4"], 0.60),
          (["B2", "F#3", "A3", "C#4", "D4", "F#4"], 0.62),
          (["G2", "D3", "F#3", "B3", "D4", "A4"], 0.64),
          (["D2", "A2", "D3", "F#3", "A3", "C#4", "E4"], 0.70)]
    for bi, (notes, g) in enumerate(ch):
        dur = BAR + (0.6 if bi < 4 else 6.0)
        chord_pad(notes, T + bi * BAR - 0.15, dur, gain=g, a=1.1, r=2.4 if bi < 4 else 5.0, bright=3000 + 300 * bi, vib=0.0008, send=0.4)
    # basses
    for bi, nm in enumerate(["G1", "F#1", "B1", "G1", "D1"]):
        d_ = BAR + (0.4 if bi < 4 else 5.0)
        M.add(sy.sine_bass(n_(nm), d_, a=0.25, r=1.0 if bi < 4 else 4.0, harm=0.35), T + bi * BAR, gain=0.62, send=0.12)
    # reaching melody (piano-ish): rising D major intervals tied to the picture
    mel = [("D5", 1.3, 0.28), ("E5", 2.5, 0.28), ("F#5", 3.3, 0.26), ("A5", 4.7, 0.34), ("E5", 4.95, 0.28),
           ("F#5", 5.6, 0.26), ("A5", 6.2, 0.28), ("B5", 6.8, 0.30)]
    for nm, tl, v in mel:
        M.add(sy.pluck(n_(nm), 3.0, v, 0.9, 1.6), T + tl, pan=0.1, send=0.55, plate=0.1)
    # thread leaves: rising shimmer
    tr = T + S6_T_REACH
    M.add(sy.glide_sine(S6_T_ARRIVE - S6_T_REACH, n_("D4"), n_("A5"), 0.10, 1.6, harm=0.2), tr, send=0.55)
    M.add(sy.whoosh(S6_T_ARRIVE - S6_T_REACH + 0.3, 700, 7000, 1.0, 0.8, 1.6, True), tr, gain=0.28, pan=0.0, send=0.5)
    # arrival at the other side (bloom) + answer
    ta = T + S6_T_ARRIVE
    for k, nm in enumerate(["A5", "E6", "C#6", "A6"]):
        M.add(sy.bell(n_(nm), 4.5, 0.26, 1.2, 1.0), ta + 0.04 * k, pan=0.5, send=0.65, plate=0.1)
    M.add(sy.boom(3.0, 80, 40, 0.8, 1.2), ta, gain=0.5, send=0.25)
    tans = T + S6_T_ANSWER
    M.add(sy.glide_sine(S6_T_MEET - S6_T_ANSWER, n_("E5"), n_("B5"), 0.10, 1.6, harm=0.2), tans, pan=0.0, send=0.55)
    M.add(sy.whoosh(S6_T_MEET - S6_T_ANSWER + 0.3, 700, 8000, 1.0, 0.8, 1.6, True), tans, gain=0.26, send=0.5)
    # climax: they meet
    tm = T + S6_T_MEET
    M.add(sy.boom(5.0, 110, 33, 1.0, 2.8), tm, gain=0.95, send=0.3)
    M.add(sy.whoosh(2.2, 10000, 500, 1.0, 1.0, 1.0, False), tm, gain=0.5, send=0.5)
    for k in range(14):
        f = pent(5, 2 + (k * 2) % 9) * (2 if k > 9 else 1)
        M.add(sy.bell(f, 4.0, 0.27 * np.exp(-k / 14.0), 1.2, 1.0), tm + 0.03 + k * 0.07, pan=rng.uniform(-0.9, 0.9), send=0.65, plate=0.08)
    # choir-ish swell on the resolution chord (formant-filtered saw stack)
    dur = 6.8
    n = int(dur * SR)
    x = np.arange(n) / SR
    env = sy.smoothstep(x / 1.8) * (1 - sy.smoothstep((x - 5.0) / 1.8))
    vox = np.zeros(n)
    for nm in ["D3", "A3", "D4", "F#4", "A4"]:
        f = n_(nm)
        for dc in (-6, 6):
            ff = f * 2 ** (dc / 1200)
            ph = 2 * np.pi * ff * x + 0.05 * np.sin(2 * np.pi * 5.2 * x)
            K = int(min(30, 9000 / ff))
            vox += sum(np.sin(k * ph) / k for k in range(1, K + 1))
    vox = sy.bp(vox, 600, 1000, 2) * 1.0 + sy.bp(vox, 1000, 1500, 2) * 0.7 + sy.bp(vox, 2300, 3200, 2) * 0.35
    vox = vox / (np.std(vox) + 1e-9) * 0.14 * env
    M.add(vox, tm - 0.2, gain=0.7, send=0.55)
    # text accents
    text_tick(T + 1.3 + 0.5, n_("A5"), 0.14)
    text_tick(T + 2.5 + 0.5, n_("D6"), 0.14)
    # title card shimmer
    tt0 = T + S6_TITLE
    M.add(sy.whoosh(1.4, 3000, 11000, 1.0, 0.9, 1.5, True), tt0 - 0.4, gain=0.18, send=0.5)
    for k, nm in enumerate(["D5", "A5", "F#6", "A6", "D7"]):
        M.add(sy.bell(n_(nm), 6.0, 0.17, 1.6, 0.9), tt0 + 0.12 * k, pan=-0.4 + 0.2 * k, send=0.75)
    M.add(sy.glide_sine(2.5, n_("D2"), n_("D3"), 0.10, 1.2), tt0 - 0.5, send=0.3)


# =====================================================================  master
def master():
    print("rendering sections...")
    s1(); print(" s1 ok")
    s2(); print(" s2 ok")
    s3(); print(" s3 ok")
    s4(); print(" s4 ok")
    s5(); print(" s5 ok")
    s6(); print(" s6 ok")
    print("reverb...")
    ir_hall = sy.make_ir(4.2, seed=1, damp=4800, rt_hf=0.5)
    ir_plate = sy.make_ir(1.3, seed=7, pre=0.006, damp=9000, rt_hf=0.7)
    for bus in (M.rev, M.pla):
        for ch in range(2):
            bus[ch] = sy.hp(bus[ch].astype(np.float64), 180, 2).astype(np.float32)
    wet = sy.convolve(M.rev, ir_hall) * 0.85 + sy.convolve(M.pla, ir_plate) * 0.8
    mix = M.dry + wet
    # scene-level automation (gain rides)
    n = mix.shape[1]
    t = np.arange(n) / SR
    g = np.ones(n)
    # S2 fade into night before the storm
    g *= 1 - 0.85 * sy.smoothstep((t - 20.0) / 1.3) * (t < 21.6) * (1 - sy.smoothstep((t - 21.4) / 0.3))
    # global fade out
    g *= 1 - sy.smoothstep((t - (TOTAL - 3.0)) / 3.0)
    g *= sy.smoothstep(t / 0.8 + 0.001)
    mix = mix * g.astype(np.float32)
    # high-pass rumble guard + gentle bus compression via tanh
    for ch in range(2):
        x_ = mix[ch].astype(np.float64)
        x_ = sy.hp(x_, 30, 4)
        x_ = x_ - 0.30 * sy.lp(x_, 95, 2)          # tame the sub region
        mix[ch] = x_.astype(np.float32)
    peak = np.max(np.abs(mix))
    print("peak before norm", peak)
    mix = mix / peak * 0.80
    mix = np.tanh(mix * 1.25) / np.tanh(1.25)
    mix = mix / np.max(np.abs(mix)) * 0.92
    out = mix[:, :int(TOTAL * SR)]
    out_i = (out.T * 32767).astype(np.int16)
    wavfile.write(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "late_light.wav"), SR, out_i)
    print("done", out.shape, "rms", np.sqrt(np.mean(out ** 2)))


if __name__ == "__main__":
    master()
