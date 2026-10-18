"""Scene definitions: shader uniforms, grade, text for each world."""
import numpy as np
from timeline import *
from text import smooth, ease_out, ease_io

DEFAULT_GRADE = dict(exposure=1.0, contrast=1.0, sat=1.0, lift=(0, 0, 0), gain=(1, 1, 1),
                     shadow=(1, 1, 1), high=(1, 1, 1), bloom=0.3, streak=0.0, streak_tint=(0.7, 0.85, 1.0),
                     vig=0.4, ca=0.002, grain=0.03, tone=0.0, bloom_thresh=0.0, fade=1.0)


def clamp01(x):
    return min(max(x, 0.0), 1.0)


def px(uvp):
    """uv (height units, y up, centre origin) -> pixel (x, y_down)"""
    return W / 2 + uvp[0] * H, H / 2 - uvp[1] * H


class Scene:
    name = ""
    gain_main = 1.5
    gain_hud = 1.0

    def grade(self, t):
        return dict(DEFAULT_GRADE)

    def render(self, eng, fbo, t, frame):
        raise NotImplementedError

    def text(self, t, main, hud):
        pass


# =============================================================== S1
class Stars(Scene):
    name = "stars"
    gain_main = 1.45
    gain_hud = 1.0

    def doomed(self, t):
        d = S1_DEATH
        if t < d - 1.0:
            return 1.0 + 0.04 * np.sin(t * 2.1), 0.35
        if t < d:
            x = t - (d - 1.0)
            return 1.0 + 3.2 * x ** 3, 0.35 + 1.4 * x ** 3
        x = t - d
        b = 26.0 * np.exp(-x * 12.0) * (1 - smooth((x - 0.22) / 0.4))
        return max(b, 0.0), 1.0 + 6.0 * np.exp(-x * 7.0)

    def hero_state(self, t):
        z = s1_scale(t)
        out = []
        for i, h in enumerate(HEROES):
            x, y = h["p"]
            x, y = x * z, y * z
            if i == 0:
                b, s = self.doomed(t)
            else:
                b, s = h["b"] * (1.0 + 0.06 * np.sin(t * 1.7 + i)), 0.3 + 0.2 * h["b"]
            out.append((x, y, b, s))
        return out

    def ring(self, t, hs):
        x = (t - S1_DEATH) / S1_RING_DUR
        if x <= 0:
            return (hs[0][0], hs[0][1], 0.0, 0.0)
        R = 0.012 + 1.62 * x ** 2.1
        inten = (0.35 + 1.4 * min(R, 1.0)) * smooth(x * 8)
        return (hs[0][0], hs[0][1], R, inten)

    def hud_reveal(self, t):
        rev = []
        for i in range(len(HEROES)):
            start = 3.35 if i == 0 else 1.5 + 0.42 * (i - 1)
            rev.append(ease_out((t - start) / 1.3))
        return rev

    def render(self, eng, fbo, t, frame):
        hs = self.hero_state(t)
        hero = np.zeros((8, 4), "f4")
        for i, h in enumerate(hs):
            hero[i] = h
        rv = self.hud_reveal(t)
        hud = np.zeros(8, "f4")
        dim = np.ones(8, "f4")
        for i, r in enumerate(rv):
            hud[i] = r
            dim[i] = 1.0 - smooth((t - 8.3) / 1.2) * 0.9
        ring = self.ring(t, hs)
        white = smooth((t - 9.0) / 1.9) ** 2.2 * 14.0
        fadein = smooth(t / 2.6)
        eng.pass_("s1_stars.frag", fbo, uTime=t, uFrame=frame, uHero=hero, uHud=hud, uHudDim=dim,
                  uRing=ring, uZoom=s1_scale(t), uWhite=white, uFadeIn=0.0 + fadein, uNHero=len(HEROES))

    def grade(self, t):
        g = dict(DEFAULT_GRADE)
        g.update(bloom=0.30, streak=0.30, vig=0.55, ca=0.0012, grain=0.04,
                 shadow=(0.92, 1.0, 1.12), high=(1.0, 0.99, 0.97), sat=1.05)
        return g

    def text(self, t, main, hud):
        col = (0.94, 0.97, 1.0)
        out = 8.4
        main.anim_text("Nothing you see", "light", 84, 150, 742, col, t, 2.3, 1.0, 0.04, out, 0.9, 0.012)
        main.anim_text("is happening now.", "light", 84, 150, 842, col, t, 3.2, 1.0, 0.04, out, 0.9, 0.012)
        # HUD labels
        rv = self.hud_reveal(t)
        for i, h in enumerate(HEROES):
            if rv[i] < 0.62:
                continue
            z = s1_scale(t)
            cx, cy = px((h["p"][0] * z, h["p"][1] * z))
            n = 0.7071
            ax, ay = cx + n * (0.034 + 0.050) * H, cy - n * (0.034 + 0.050) * H
            q = smooth((rv[i] - 0.62) / 0.38)
            dim = 1.0 - smooth((t - 8.3) / 1.2) * 0.9
            nch = int(len(h["ly"]) * q + 0.999)
            hud.text(h["ly"][:nch], "mono", 21, ax + 8, ay - 28, (0.72, 0.86, 1.0), tracking=0.06, alpha=0.9 * dim)


# =============================================================== S2
class Sun(Scene):
    name = "sun"
    gain_main = 1.5
    gain_hud = 1.0

    def prog(self, t):
        return clamp01((t - S2_LAUNCH) / (S2_ARRIVE - S2_LAUNCH))

    def tick_t(self, k):
        f = 60.0 * (k + 1) / S2_TOTAL_SEC
        return S2_LAUNCH + f * (S2_ARRIVE - S2_LAUNCH)

    def render(self, eng, fbo, t, frame):
        ticks = np.zeros(8, "f4")
        for k in range(8):
            dt = t - self.tick_t(k)
            ticks[k] = np.exp(-dt * 5.0) if dt >= 0 else 0.0
        arr = t - S2_ARRIVE
        flash = np.exp(-max(arr, 0) * 2.2) * smooth(arr / 0.06 + 1) if arr >= -0.06 else 0.0
        lit = smooth(arr / 1.6) if arr > 0 else 0.0
        white = 14.0 * np.exp(-max(t, 0.0) * 3.0)
        fadeout = 1.0 - smooth((t - 9.6) / 1.6)
        zoom = 1.0 + 0.007 * (t + 0.5)
        eng.pass_("s2_sun.frag", fbo, uTime=t, uFrame=frame, uSunC=S2_SUN_C, uRs=S2_RS, uEarthC=S2_EARTH,
                  uRe=S2_RE, uLineY=S2_LINE_Y, uLimbX=S2_LIMB_X, uEdgeX=S2_EDGE_X, uProg=self.prog(t),
                  uTick=ticks, uLit=lit, uFlash=flash, uArrT=arr, uWhite=white, uZoom=zoom,
                  uLineA=smooth((t - 1.2) / 0.8), uFadeOut=fadeout)

    def grade(self, t):
        g = dict(DEFAULT_GRADE)
        g.update(exposure=1.0, bloom=0.36, streak=0.30, streak_tint=(1.0, 0.75, 0.5), vig=0.5, ca=0.0014,
                 grain=0.04, shadow=(1.08, 0.97, 0.9), high=(1.0, 0.96, 0.9), sat=1.05)
        return g

    def text(self, t, main, hud):
        col = (1.0, 0.96, 0.9)
        gold = (1.0, 0.74, 0.40)
        out = 9.3
        main.anim_text("The Sun is", "light", 90, 850, 214, col, t, 2.2, 1.0, 0.04, out, 0.9, 0.012)
        # "eight minutes" in gold, " old." in white
        s = "eight minutes old."
        xs, total = layout_("light", 90, s)
        x0, y0 = 850, 318
        for ch_i, ch in enumerate(s):
            pass
        main.anim_text("eight minutes", "med", 90, x0, y0, gold, t, 3.0, 1.0, 0.04, out, 0.9, 0.012)
        wlen = layout_("med", 90, "eight minutes")[1] + 0.34 * 90
        main.anim_text("old.", "light", 90, x0 + wlen, y0, col, t, 3.55, 1.0, 0.04, out, 0.9, 0.012)
        # HUD: timer + labels
        f = self.prog(t)
        secs = int(S2_TOTAL_SEC * f)
        hud_a = smooth((t - 1.4) / 0.8) * (1.0 - smooth((t - 9.2) / 1.0))
        mm, ss = divmod(secs, 60)
        hud.text(f"{mm:02d}:{ss:02d}", "mono_l", 46, W / 2 + 0.255 * H, H / 2 - S2_LINE_Y * H + 38, (1.0, 0.84, 0.66), tracking=0.04, align="c", alpha=hud_a)
        hud.text("LIGHT IN TRANSIT", "mono", 17, W / 2 + 0.255 * H, H / 2 - S2_LINE_Y * H + 98, (1.0, 0.78, 0.55), tracking=0.28, align="c", alpha=0.75 * hud_a)
        for k in range(8):
            tx = S2_LIMB_X + (S2_EDGE_X - S2_LIMB_X) * 60.0 * (k + 1) / S2_TOTAL_SEC
            hud.text(f"{k+1}", "mono", 15, W / 2 + tx * H, H / 2 - S2_LINE_Y * H - 52, (1.0, 0.82, 0.6), align="c", alpha=0.55 * hud_a)
        hud.text("MIN", "mono", 13, W / 2 + S2_LIMB_X * H - 6, H / 2 - S2_LINE_Y * H - 52, (1.0, 0.82, 0.6), tracking=0.2, align="r", alpha=0.4 * hud_a)
        hud.text("149,600,000 km", "mono", 15, W / 2 + 0.255 * H, H / 2 - S2_LINE_Y * H + 142, (1.0, 0.8, 0.6), tracking=0.16, align="c", alpha=0.45 * hud_a)


def layout_(fname, size, s):
    from text import layout
    return layout(s, fname, size)


# =============================================================== S3
def gen_bolt(seed, x0, y0, x1, y1, nbranch=6):
    rng = np.random.RandomState(seed)
    segs = []   # ax, ay, bx, by, s, bright

    def jag(a, b, disp, depth, s0, s1, br):
        if depth == 0:
            segs.append((a[0], a[1], b[0], b[1], 0.5 * (s0 + s1), br))
            return
        d = b - a
        n = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-9)
        m = (a + b) / 2 + n * rng.randn() * disp
        jag(a, m, disp * 0.56, depth - 1, s0, 0.5 * (s0 + s1), br)
        jag(m, b, disp * 0.56, depth - 1, 0.5 * (s0 + s1), s1, br)

    a, b = np.array([x0, y0]), np.array([x1, y1])
    jag(a, b, 0.07, 5, 0.0, 1.0, 1.0)
    main = [s for s in segs]
    for k in range(nbranch):
        s = main[rng.randint(3, len(main) - 4)]
        p0 = np.array([s[0], s[1]])
        ang = np.arctan2(y1 - y0, x1 - x0) + rng.choice([-1, 1]) * rng.uniform(0.35, 0.85)
        ln = rng.uniform(0.10, 0.26)
        p1 = p0 + ln * np.array([np.cos(ang), np.sin(ang)])
        if p1[1] < y1:
            p1[1] = y1 + 0.02
        n0 = len(segs)
        jag(p0, p1, 0.02, 3, s[4], s[4] + 0.12, 0.42)
        if rng.rand() < 0.5 and len(segs) > n0 + 2:
            t_ = segs[n0 + 2]
            q0 = np.array([t_[0], t_[1]])
            ang2 = ang + rng.choice([-1, 1]) * 0.6
            q1 = q0 + 0.09 * np.array([np.cos(ang2), np.sin(ang2)])
            jag(q0, q1, 0.012, 2, t_[4], t_[4] + 0.08, 0.25)
    return segs[:160]


class Storm(Scene):
    name = "storm"
    gain_main = 1.5
    gain_hud = 1.0

    def __init__(self):
        yb = S3_YH - 1.0 / S3_BOLT_BASE_ZW
        self.yb = yb
        self.segs = gen_bolt(11, S3_BOLT_X + 0.06, 0.66, S3_BOLT_X, yb)
        self.segs2 = gen_bolt(5, 0.58, 0.66, 0.66, S3_YH - 0.03, 4)   # secondary far bolt

    def bolt_state(self, t):
        ts = S3_STRIKE
        prog = clamp01((t - (ts - 0.13)) / 0.13) if t < ts else 1.0
        dt = t - ts
        if dt < -0.13:
            return 0.0, 0.0
        if dt < 0:
            return prog, 0.25 + 0.5 * prog
        flick = 1.0 * np.exp(-dt * 7.0) + 0.8 * np.exp(-abs(dt - 0.10) * 30.0) * (dt > 0.04) + 0.55 * np.exp(-abs(dt - 0.21) * 24.0) * (dt > 0.14)
        fade = 1.0 - smooth((dt - 0.35) / 0.35)
        return 1.0, 3.2 * flick * fade

    def sheet(self, t):
        v = 0.0
        # faint precursor
        v += 0.35 * np.exp(-abs(t - 0.95) * 4.0) * (t > 0.85)
        v += 0.22 * np.exp(-abs(t - 1.35) * 9.0) * (t > 1.25)
        # reacting to main strike
        dt = t - S3_STRIKE
        v += 0.65 * np.exp(-max(dt, 0) * 3.2) * (dt > -0.02) * (1 - smooth((dt - 0.1) / 1.0) * 0.4)
        # distant answering flash
        v += 0.5 * np.exp(-abs(t - 5.55) * 7.0) * (t > 5.45)
        # closing flash
        v += 2.6 * smooth((t - 7.55) / 0.35) * (t > 7.5)
        return v

    def shake(self, t):
        dt = t - (S3_STRIKE + S3_DELAY)
        if dt < 0:
            return (0.0, 0.0)
        a = 0.016 * np.exp(-dt * 3.2)
        return (a * np.sin(dt * 71.0) * np.sin(dt * 13.0 + 1), a * 0.8 * np.sin(dt * 83.0 + 2.0))

    def render(self, eng, fbo, t, frame):
        bp, bi = self.bolt_state(t)
        segs = np.zeros((160, 4), "f4")
        segp = np.zeros((160, 2), "f4")
        n = 0
        for sgm in self.segs:
            segs[n] = sgm[:4]
            segp[n] = (sgm[4], sgm[5])
            n += 1
        dt = t - S3_STRIKE
        rr = S3_BOLT_BASE_ZW * dt / S3_DELAY if dt > 0 else 0.0
        zs = S3_BOLT_BASE_ZW
        ringA = 1.0 if dt > 0 else 0.0
        ringA *= 1.0 - smooth((dt - S3_DELAY - 0.2) / 1.0)
        sh = self.shake(t)
        thunder = np.exp(-max(dt - S3_DELAY, 0) * 2.5) if dt > S3_DELAY else 0.0
        fadein = smooth(t / 1.1 + 0.02) if t < 1.1 else 1.0
        eng.pass_("s3_storm.frag", fbo, uTime=t, uFrame=frame, uSeg=segs, uSegP=segp, uNSeg=n, uBoltProg=bp, uBoltI=bi,
                  uBoltX=S3_BOLT_X, uSheet=self.sheet(t), uSheetC=(S3_BOLT_X - 0.15, 0.25), uYh=S3_YH, uRingR=rr,
                  uRingA=ringA, uStrikeW=(S3_BOLT_X * zs, zs), uShake=sh, uFadeIn=fadein, uThunder=thunder, uWhite=0.0)

    def grade(self, t):
        g = dict(DEFAULT_GRADE)
        g.update(exposure=1.35, bloom=0.55, streak=0.55, streak_tint=(0.65, 0.75, 1.0), vig=0.55, ca=0.0018,
                 grain=0.05, shadow=(0.9, 1.0, 1.15), high=(0.95, 0.98, 1.05), sat=0.95, contrast=1.04)
        return g

    def text(self, t, main, hud):
        col = (0.90, 0.94, 1.0)
        out = 6.9
        sh = self.shake(t)
        ox, oy = sh[0] * H, -sh[1] * H
        main.anim_text("Thunder is lightning,", "light", 88, 140 + ox, 118 + oy, col, t, 2.35, 1.0, 0.04, out, 0.9, 0.012)
        main.anim_text("running late.", "light", 88, 140 + ox, 222 + oy, col, t, 3.3, 1.0, 0.04, out, 0.9, 0.012)
        dt = t - S3_STRIKE
        a = smooth((dt + 0.1) / 0.5) * (1.0 - smooth((t - 6.6) / 0.8))
        d = min(max(dt, 0.0), S3_DELAY)
        x = W - 150
        hud.text(f"{d:0.1f} s", "mono_l", 56, x, 820, (0.78, 0.88, 1.0), tracking=0.03, align="r", alpha=a)
        hud.text("FLASH  →  THUNDER", "mono", 16, x, 892, (0.7, 0.82, 1.0), tracking=0.24, align="r", alpha=0.7 * a)
        hud.text("≈ 1 km", "mono", 16, x, 918, (0.7, 0.82, 1.0), tracking=0.24, align="r", alpha=0.45 * a)


# =============================================================== S4
class Neuro(Scene):
    name = "neuro"
    gain_main = 1.45
    gain_hud = 1.0

    def __init__(self):
        self.built = False

    def build(self, eng):
        import moderngl, neuro
        from engine import read_shader
        self.net = neuro.get_net()
        n = self.net
        ctx = eng.ctx
        self.rprog = ctx.program(vertex_shader=read_shader("s4_ribbon.vert"), fragment_shader=read_shader("s4_ribbon.frag"))
        self.pprog = ctx.program(vertex_shader=read_shader("s4_point.vert"), fragment_shader=read_shader("s4_point.frag"))
        self.rvbo = ctx.buffer(n.rv_arr.tobytes())
        self.ribo = ctx.buffer(n.ri_arr.tobytes())
        self.pvbo = ctx.buffer(n.pv_arr.tobytes())
        self.rvao = ctx.vertex_array(self.rprog, [(self.rvbo, "3f 3f 3f 1f 1f 1f 1f 1f 1f 1f",
                                                   "aPos", "aPrev", "aNext", "aSide", "aD", "aW", "aA", "aC", "aB", "aSeed")],
                                     index_buffer=self.ribo)
        self.pvao = ctx.vertex_array(self.pprog, [(self.pvbo, "3f 1f 1f 1f 1f 1f 1f",
                                                   "aPos", "aSize", "aD", "aA", "aC", "aB", "aSeed")])
        self.npts = len(n.pv_arr)
        self.built = True
        self.moderngl = moderngl

    def front(self, t):
        return S4_D0 + S4_V * (t - S4_T0) if t > S4_T0 else S4_D0 - 5.0

    @property
    def arrive(self):
        import neuro
        return neuro.arrival_time()

    def cam(self, t):
        a = ease_io((t - 0.5) / (self.arrive - 0.5 + 0.6))
        cx = 6.3 + (-5.6 - 6.3) * a
        cy = 0.15 * np.sin(t * 0.35) + (0.2 * a)
        cz = S4_CAMD + 0.4 * np.sin(t * 0.22)
        return np.array([cx, cy, cz])

    def project(self, w, cam):
        p = w - cam
        d = -p[2]
        return np.array([p[0] / d * S4_FOCAL, p[1] / d * S4_FOCAL])

    def render(self, eng, fbo, t, frame):
        if not self.built:
            self.build(eng)
        mgl = self.moderngl
        ctx = eng.ctx
        cam = self.cam(t)
        fr = self.front(t)
        net = self.net
        # glow bounce positions
        fp = main_pt = None
        import neuro
        if fr < net.axon_len:
            wp = neuro.main_point_at_D(net, fr)
            gl_c = self.project(wp, cam)
            gl_a = smooth((fr + 3.0) / 3.0) * 1.0
        else:
            gl_c = self.project(neuro.main_point_at_D(net, net.axon_len), cam)
            gl_a = 0.0
        gl_a *= smooth((t - 0.8) / 0.6)
        brain = self.project(net.cluster, cam)
        arrive = clamp01((fr - net.axon_len) / 4.0)
        g2a = smooth(arrive * 1.4) * (1.0 - smooth((t - 6.8) / 1.4) * 0.6)
        fadein = smooth(t / 1.0) if t < 1.0 else 1.0
        eng.pass_("s4_bg.frag", fbo, uTime=t, uFrame=frame, uGlowC=tuple(gl_c), uGlowA=gl_a, uGlow2C=tuple(brain),
                  uGlow2A=g2a, uFadeIn=fadein, uCamP=(cam[0], cam[1]), uWhite=6.0 * smooth((t - 7.2) / 1.3) ** 2)
        ctx.enable(mgl.BLEND)
        ctx.blend_func = mgl.ONE, mgl.ONE
        ctx.enable(mgl.PROGRAM_POINT_SIZE)
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        for prog in (self.rprog, self.pprog):
            for k, v in dict(uCam=tuple(cam), uFocal=S4_FOCAL, uFocus=S4_CAMD, uCoc=0.075, uAspect=W / H, uFront=float(fr),
                             uTime=float(t), uIdle=0.5, uH=float(H)).items():
                if k in prog:
                    prog[k].value = v
        self.rvao.render(mgl.TRIANGLES)
        self.pvao.render(mgl.POINTS, vertices=self.npts)
        ctx.disable(mgl.BLEND)

    def grade(self, t):
        g = dict(DEFAULT_GRADE)
        g.update(exposure=0.95, bloom=0.50, streak=0.0, vig=0.55, ca=0.0022, grain=0.05, sat=1.08,
                 shadow=(0.9, 1.05, 1.08), high=(1.0, 0.98, 1.02))
        return g

    def text(self, t, main, hud):
        col = (0.90, 1.0, 0.97)
        out = 7.0
        main.anim_text("You feel it all", "light", 88, 140, 742, col, t, 2.3, 1.0, 0.04, out, 0.9, 0.012)
        main.anim_text("a tenth of a second late.", "light", 88, 140, 846, col, t, 3.15, 1.0, 0.04, out, 0.9, 0.012)
        net_len = 15.5
        # timer
        f = clamp01((t - S4_T0) / (self.arrive - S4_T0))
        a = smooth((t - 0.8) / 0.6) * (1.0 - smooth((t - 6.8) / 0.8))
        x = W - 150
        hud.text(f"{0.100 * f:0.3f} s", "mono_l", 56, x, 118, (0.62, 1.0, 0.9), tracking=0.03, align="r", alpha=a)
        hud.text("NERVE  →  BRAIN", "mono", 16, x, 190, (0.55, 0.95, 0.85), tracking=0.24, align="r", alpha=0.75 * a)
        hud.text("SLOWED 32×", "mono", 16, x, 216, (0.55, 0.95, 0.85), tracking=0.24, align="r", alpha=0.45 * a)


# =============================================================== S5
class Paper(Scene):
    name = "paper"
    gain_main = 1.0
    gain_hud = 1.0

    def head(self, i, t):
        phi0, d, turns, t0, t1, lab = S5_STREAMS[i]
        u = clamp01((t - t0) / (t1 - t0))
        smax = 1.0 - S5_RD / S5_R0
        sh = (1.0 - (1.0 - u) ** 2) * smax
        rH = S5_R0 * (1.0 - sh)
        aH = phi0 + d * turns * sh
        return (S5_C[0] + rH * np.cos(aH), S5_C[1] + rH * np.sin(aH)), u

    def render(self, eng, fbo, t, frame):
        strs = np.zeros((4, 4), "f4")
        strt = np.zeros((4, 4), "f4")
        for i, (phi0, d, turns, t0, t1, lab) in enumerate(S5_STREAMS):
            strs[i] = (phi0, d, turns, 0)
            strt[i] = (t0, t1, i, 0)
        ink = np.array(S5_INKS, "f4")
        gold = smooth((t - S5_GOLD_T) / 0.7) if t > S5_GOLD_T else 0.0
        white = 6.0 * (1 - smooth(t / 0.9)) ** 2
        eng.pass_("s5_paper.frag", fbo, uTime=t, uFrame=frame, uC=S5_C, uR0=S5_R0, uRd=S5_RD, uStr=strs, uStrT=strt,
                  uInk=ink, uGold=gold, uWhite=white, uFadeIn=smooth((t - 0.3) / 0.8))

    def grade(self, t):
        g = dict(DEFAULT_GRADE)
        gold = smooth((t - S5_GOLD_T) / 0.7) if t > S5_GOLD_T else 0.0
        g.update(exposure=1.0, bloom=0.08 + 0.55 * gold, streak=0.0, vig=0.12, ca=0.0006, grain=0.028, tone=1.0, sat=1.04,
                 bloom_thresh=0.9, contrast=1.02)
        return g

    def text(self, t, main, hud):
        ink = (0.006, 0.008, 0.016)
        org = (0.98 ** 2.2, 0.38 ** 2.2, 0.06 ** 2.2)
        out = None
        x = 140
        main.anim_text("Everything", "semi", 128, x, 262, ink, t, 0.9, 0.9, 0.028, 7.1, 0.5, -0.03, 90.0, 0.0)
        main.anim_text("arrives", "semi", 128, x, 408, ink, t, 1.35, 0.9, 0.028, 7.1, 0.5, -0.03, 90.0, 0.0)
        main.anim_text("late.", "semi", 128, x, 554, org, t, 5.25, 1.0, 0.04, 7.1, 0.5, -0.03, 90.0, 0.0)
        # stream labels
        for i, (phi0, d, turns, t0, t1, lab) in enumerate(S5_STREAMS):
            (hx, hy), u = self.head(i, t)
            if u <= 0.01:
                continue
            a = smooth(u * 6.0) * (1.0 - smooth((t - t1 - 0.15) / 0.6))
            cx, cy = px((hx, hy))
            ink_i = S5_INKS[i]
            dark = (ink_i[0] * 0.5, ink_i[1] * 0.5, ink_i[2] * 0.5)
            ox, oy = cx - px(S5_C)[0], cy - px(S5_C)[1]
            n = (ox ** 2 + oy ** 2) ** 0.5 + 1e-6
            lx, ly = cx + ox / n * 46, cy + oy / n * 46
            hud.text(lab, "mono", 22, lx, ly - 11, dark, tracking=0.06, align=("l" if ox >= 0 else "r"), alpha=a)
        hud.text("FIG. 5   ARRIVALS", "mono", 15, W - 90, 78, (0.03, 0.035, 0.06), tracking=0.28, align="r", alpha=0.7 * smooth((t - 0.5) / 0.8))


# =============================================================== S6
class Reach(Scene):
    name = "reach"
    gain_main = 1.5
    gain_hud = 1.0

    def heads(self, t):
        a = clamp01((t - S6_T_REACH) / (S6_T_ARRIVE - S6_T_REACH))
        a = ease_io(a)
        b = clamp01((t - S6_T_ANSWER) / (S6_T_MEET - S6_T_ANSWER))
        b = ease_io(b)
        return a, b

    def render(self, eng, fbo, t, frame):
        a, b = self.heads(t)
        orbL = smooth((t - 0.2) / 1.0)
        orbR = smooth((t - 0.6) / 1.0)
        # orbs swell when answered / reached
        orbL *= 1.0 + 0.7 * smooth((t - S6_T_MEET) / 0.6) + 0.25 * smooth((t - S6_T_REACH) / 0.5)
        orbR *= 1.0 + 0.7 * smooth((t - S6_T_ARRIVE) / 0.5)
        ringL = t - S6_T_MEET if t > S6_T_MEET else -1.0
        ringR = t - S6_T_ARRIVE if t > S6_T_ARRIVE else -1.0
        glow = 0.30 + smooth((t - 3.0) / 6.0) * 0.40 + 0.18 * smooth((t - S6_T_MEET) / 1.5) - 0.52 * smooth((t - 9.0) / 1.8)
        climax = smooth((t - S6_T_MEET) / 1.2) * (1.0 - 0.6 * smooth((t - 9.0) / 1.8))
        # arrival also gives a smaller rays burst for right orb
        zoom = 1.0 + 0.0045 * (t + 0.6)
        eng.pass_("s6_reach.frag", fbo, uTime=t, uFrame=frame, uOrbL=S6_ORB_L, uOrbR=S6_ORB_R, uOrbI=(orbL, orbR),
                  uHeadA=a, uHeadB=b, uRing=(ringL, ringR), uGlow=glow, uClimax=climax, uFadeIn=1.0,
                  uYh=S6_YH, uZoom=zoom, uStarA=1.0 - smooth((t - 2.0) / 5.0))

    def grade(self, t):
        g = dict(DEFAULT_GRADE)
        fade = 1.0 - smooth((t - 12.1) / 1.2)
        g.update(exposure=0.95 * (1.0 - 0.20 * smooth((t - 9.0) / 1.6)), bloom=0.50, streak=0.45, streak_tint=(1.0, 0.72, 0.45), vig=0.50, ca=0.0016, grain=0.04,
                 shadow=(1.05, 0.95, 1.12), high=(1.0, 0.95, 0.90), sat=1.12, fade=fade)
        return g

    def text(self, t, main, hud):
        col = (1.0, 0.96, 0.90)
        fo = S6_TITLE - 0.4
        # "Reach first." serif italic, centred
        size = 168
        s1, s2 = "Reach", "first."
        from text import layout
        xs1, w1 = layout(s1, "serif_i", size)
        xs2, w2 = layout(s2, "serif_i", size)
        gap = 0.28 * size
        total = w1 + gap + w2
        x0 = W / 2 - total / 2
        y0 = 150
        main.anim_text(s1, "serif_i", size, x0, y0, col, t, 1.3, 1.1, 0.05, fo, 0.9, 0.0, 36.0, 18.0)
        main.anim_text(s2, "serif_i", size, x0 + w1 + gap, y0, (1.0, 0.86, 0.66), t, 2.5, 1.1, 0.05, fo, 0.9, 0.0, 36.0, 18.0)
        # title card
        ta = smooth((t - S6_TITLE) / 1.3)
        tt = "LATE LIGHT"
        xs, tw = layout(tt, "light", 92, 0.42)
        main.text(tt, "light", 92, W / 2 + 0.21 * 92 - 0.0, 452, (1.0, 0.95, 0.88), tracking=0.42, align="c", alpha=ta, blur=(1 - ta) * 10)
        # thin rules
        rule_w = 360 * ta
        for sx in (-1, 1):
            pass
        hud.text("2026", "mono", 18, W / 2, 600, (1.0, 0.88, 0.7), tracking=0.5, align="c", alpha=0.7 * smooth((t - S6_TITLE - 0.6) / 1.2))


SCENE_OBJS = {"stars": Stars(), "sun": Sun(), "storm": Storm(), "neuro": Neuro(), "paper": Paper(), "reach": Reach()}
TRANS_MODE = [2, 1, 2, 1, 3]
