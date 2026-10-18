"""Procedural nerve + brain network (3D ribbons / point sprites)."""
import numpy as np
from timeline import *
from text import smooth, ease_io


def catmull(P, n):
    P = np.asarray(P, float)
    m = len(P)
    ext = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(m - 1):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1])
    return np.array(out)


def unit(v):
    return v / (np.linalg.norm(v) + 1e-9)


class Net:
    def __init__(self, seed=7):
        self.rng = np.random.RandomState(seed)
        self.rv = []     # ribbon vertex rows
        self.ri = []     # indices
        self.pv = []     # point rows
        self.nv = 0
        self.main_pts = None
        self.main_D = None

    # ----------------------------------------------------------- ribbons
    def fiber(self, pts, D0, w, a, c, b, beads=False, taper=0.0, seed=None, cend=None):
        pts = np.asarray(pts, float)
        N = len(pts)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        s = np.concatenate([[0.0], np.cumsum(seg)])
        D = D0 + s
        width = np.full(N, w)
        if beads:
            width = w * (0.50 + 0.50 * np.sin(np.pi * s / 0.75) ** 2)
        if taper:
            width = width * (1.0 - taper * s / max(s[-1], 1e-6))
        seed = self.rng.rand() if seed is None else seed
        base = self.nv
        cs = np.full(N, c) if cend is None else np.linspace(c, cend, N)
        for i in range(N):
            prv = pts[max(i - 1, 0)]
            nxt = pts[min(i + 1, N - 1)]
            for side in (-1.0, 1.0):
                self.rv.append([*pts[i], *prv, *nxt, side, D[i], width[i], a, cs[i], b, seed])
        for i in range(N - 1):
            v = base + 2 * i
            self.ri += [v, v + 1, v + 2, v + 1, v + 3, v + 2]
        self.nv += 2 * N
        return D[-1], pts[-1]

    def point(self, pos, size, D, a, c, b, seed=None):
        seed = self.rng.rand() if seed is None else seed
        self.pv.append([*pos, size, D, a, c, b, seed])


def build():
    net = Net(7)
    rng = net.rng
    # ---- main axon
    ctrl = np.array([[7.6, -1.6, 0.4], [5.0, -0.6, -0.5], [2.0, 0.6, 0.3], [-1.0, 0.1, -0.2],
                     [-3.6, 1.1, 0.2], [-5.4, 1.3, 0.0]])
    path = catmull(ctrl, 60)
    Dend, pend = net.fiber(path, 0.0, 0.062, 1.0, 0.12, 1.0, beads=True)
    net.main_pts = path
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    net.main_D = np.concatenate([[0.0], np.cumsum(seg)])
    net.axon_len = Dend
    # tinted shaft (thin, continuous) under the beads
    net.fiber(path, 0.0, 0.016, 1.0, 0.12, 0.8)

    # ---- fingertip terminals (fan)
    start = np.array([7.6, -1.6, 0.4])
    for k in range(16):
        tip = np.array([rng.uniform(8.9, 10.8), rng.uniform(-3.6, 1.4), rng.uniform(-1.6, 1.6)])
        mid = (tip + start) / 2 + rng.randn(3) * 0.45
        pts = catmull([tip, mid, start], 14)
        L = np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1))
        net.fiber(pts, -L, 0.026 + 0.012 * rng.rand(), 1.0, 0.0, 0.9, taper=0.0)
        net.point(tip, 0.045, -L, 1.0, 0.0, 1.0)
        # tiny secondary twigs at tip
        for j in range(2):
            d = unit(rng.randn(3) + np.array([1.0, 0, 0]))
            pts2 = catmull([tip, tip + d * 0.35 + rng.randn(3) * 0.08, tip + d * 0.7], 6)
            net.fiber(pts2, -L - 0.7, 0.014, 1.0, 0.0, 0.8)
    # sensory receptor bulb
    net.point(np.array([9.6, -1.4, 0.4]), 0.16, -3.6, 1.0, 0.0, 1.0)

    # ---- brain cluster
    C = np.array([-7.6, 0.7, -0.6])
    R = np.array([2.7, 2.3, 1.7])
    # branching tree from the end of the axon
    terminals = []

    def grow(pos, dirv, D, level, maxlevel, length):
        nb = 3 if level == 0 else 2
        for _ in range(nb):
            tgt = unit(C - pos + rng.randn(3) * 1.6)
            d = unit(dirv * 0.55 + tgt * 0.55 + rng.randn(3) * 0.55)
            L = length * (0.75 + 0.5 * rng.rand())
            mid = pos + d * L * 0.5 + rng.randn(3) * 0.15 * L
            pts = catmull([pos, mid, pos + d * L], 8)
            w = 0.052 * (0.72 ** level)
            cc = 0.45 + 0.1 * level
            D1, p1 = net.fiber(pts, D, w, 1.0, cc, 1.0, taper=0.15)
            if level < maxlevel:
                grow(p1, d, D1, level + 1, maxlevel, length * 0.72)
            else:
                terminals.append((p1, D1))
    grow(pend, np.array([-1.0, 0.1, 0.0]), Dend, 0, 3, 1.6)
    # cluster somas: Dijkstra-like cascade from terminals
    n_soma = 120
    somas = []
    for _ in range(n_soma):
        p = C + rng.randn(3) * R * 0.55
        somas.append(p)
    somas = np.array(somas)
    lit = [(p, D) for p, D in terminals]
    for p, D in terminals:
        net.point(p, 0.07, D, 1.0, 0.6, 1.0)
    order = list(range(n_soma))
    D_soma = np.zeros(n_soma)
    done = np.zeros(n_soma, bool)
    # repeatedly attach the soma that is cheapest to reach
    while not done.all():
        best = None
        for i in range(n_soma):
            if done[i]:
                continue
            for (p, D) in lit:
                dl = np.linalg.norm(somas[i] - p)
                if best is None or D + dl < best[0]:
                    best = (D + dl, i, p, D)
        Dtot, i, p, D = best
        mid = (p + somas[i]) / 2 + rng.randn(3) * 0.18
        pts = catmull([p, mid, somas[i]], 8)
        net.fiber(pts, D, 0.020, 1.0, min(0.55 + 0.02 * len(lit) / 10, 1.0), 0.9)
        D_soma[i] = Dtot
        done[i] = True
        lit.append((somas[i], Dtot))
        size = 0.055 + 0.075 * rng.rand()
        net.point(somas[i], size, Dtot, 1.0, min(0.6 + (Dtot - Dend) * 0.05, 1.0), 1.0)
        # dendrites
        for _ in range(rng.randint(3, 6)):
            d = unit(rng.randn(3))
            L = 0.45 + 0.5 * rng.rand()
            q0 = somas[i] + d * size * 0.6
            pts = catmull([q0, q0 + d * L * 0.5 + rng.randn(3) * 0.08, q0 + d * L + rng.randn(3) * 0.1], 5)
            Dd, pd = net.fiber(pts, Dtot, 0.012, 1.0, 0.9, 0.9, taper=0.5)
            if rng.rand() < 0.5:
                for _k in range(2):
                    d2 = unit(d + rng.randn(3) * 0.8)
                    pts2 = catmull([pd, pd + d2 * 0.2, pd + d2 * 0.4], 4)
                    net.fiber(pts2, Dd, 0.008, 1.0, 0.95, 0.8, taper=0.6)
    # extra cross-links for web density
    for _ in range(40):
        i, j = rng.randint(0, n_soma, 2)
        if i == j:
            continue
        a, b = somas[i], somas[j]
        if np.linalg.norm(a - b) > 2.2:
            continue
        mid = (a + b) / 2 + rng.randn(3) * 0.25
        pts = catmull([a, mid, b], 8)
        D0 = min(D_soma[i], D_soma[j])
        net.fiber(pts, D0, 0.010, 1.0, 0.9, 0.8)

    # ---- background: far fibres + bokeh somas, foreground blurred strands
    for k in range(70):
        z = rng.uniform(-6.0, -1.8)
        x = rng.uniform(-14, 12)
        y = rng.uniform(-4, 4)
        ctrl = []
        ang = rng.uniform(-0.6, 0.6)
        for i in range(7):
            ctrl.append([x, y, z + rng.randn() * 0.3])
            ang += rng.randn() * 0.35
            x += 1.8 * np.cos(ang) * rng.choice([-1, 1]) * 0 + 1.9 * np.cos(ang)
            y += 1.9 * np.sin(ang)
        pts = catmull(ctrl, 10)
        net.fiber(pts, rng.rand() * 50, 0.020 + 0.02 * rng.rand(), 0.0, 0.3, 0.30 + 0.35 * rng.rand())
    for k in range(40):
        p = np.array([rng.uniform(-14, 12), rng.uniform(-4.5, 4.5), rng.uniform(-8, -2.5)])
        net.point(p, 0.10 + 0.28 * rng.rand(), rng.rand() * 50, 0.0, 0.3, 0.25 + 0.4 * rng.rand())
    for k in range(5):
        z = rng.uniform(3.2, 4.2)
        x0 = rng.uniform(-9, 9)
        ctrl = [[x0 + 2.2 * i + rng.randn() * 0.3, rng.uniform(-3, 3) * 0.5 + 0.6 * i * rng.choice([-1, 1]), z + rng.randn() * 0.2] for i in range(5)]
        pts = catmull(ctrl, 10)
        net.fiber(pts, 0.0, 0.035, 0.0, 0.3, 0.22)
    # marine snow
    for k in range(220):
        p = np.array([rng.uniform(-13, 13), rng.uniform(-5, 5), rng.uniform(-6, 5)])
        net.point(p, 0.010 + 0.025 * rng.rand(), rng.rand() * 50, 0.0, 0.3, 0.6 + rng.rand())

    rv = np.array(net.rv, "f4")
    ri = np.array(net.ri, "i4")
    pv = np.array(net.pv, "f4")
    net.rv_arr, net.ri_arr, net.pv_arr = rv, ri, pv
    net.cluster = C
    return net


def main_point_at_D(net, D):
    D = np.clip(D, 0, net.main_D[-1])
    x = np.interp(D, net.main_D, net.main_pts[:, 0])
    y = np.interp(D, net.main_D, net.main_pts[:, 1])
    z = np.interp(D, net.main_D, net.main_pts[:, 2])
    return np.array([x, y, z])


_NET = None


def get_net():
    global _NET
    if _NET is None:
        _NET = build()
    return _NET


def arrival_time():
    """scene-local time when the impulse reaches the brain tree"""
    n = get_net()
    return S4_T0 + (n.axon_len - S4_D0) / S4_V


def bead_times():
    """scene-local times at which the front crosses each myelin bead along the axon (spacing 0.75)"""
    n = get_net()
    out = []
    k = int(np.ceil(S4_D0 / 0.75))
    while k * 0.75 <= n.axon_len:
        out.append(S4_T0 + (k * 0.75 - S4_D0) / S4_V)
        k += 1
    return out
