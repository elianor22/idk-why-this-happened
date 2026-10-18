"""Shared timeline: every visual and audio event keys off these numbers."""

W, H = 1920, 1080
FPS = 30
BPM = 90
BEAT = 60.0 / BPM
BAR = 4 * BEAT  # 2.6667 s

# (name, start bar, length bars)
SCENE_DEF = [
    ("stars", 0, 4),
    ("sun", 4, 4),
    ("storm", 8, 3),
    ("neuro", 11, 3),
    ("paper", 14, 3),
    ("reach", 17, 5),
]
SCENES = []
for _n, _b, _l in SCENE_DEF:
    SCENES.append(dict(name=_n, t0=_b * BAR, t1=(_b + _l) * BAR))
TOTAL = SCENES[-1]["t1"]
NFRAMES = int(round(TOTAL * FPS))

# transition i joins scene i -> i+1 ; half-width seconds
TRANS_HW = [0.45, 0.45, 0.45, 0.45, 0.60]

# ---------------------------------------------------------------- S1 stars
# hero stars (uv units = screen heights, y up, centre origin) and light-years
HEROES = [
    dict(p=(0.36, 0.14), ly="1,800 ly", b=1.0),   # doomed star
    dict(p=(-0.55, 0.22), ly="430 ly", b=0.8),
    dict(p=(-0.12, -0.10), ly="2,600 ly", b=0.7),
    dict(p=(0.52, -0.21), ly="12,000 ly", b=0.75),
    dict(p=(-0.74, -0.04), ly="4.2 ly", b=0.9),
    dict(p=(0.06, 0.33), ly="90 ly", b=0.65),
]
S1_DEATH = 5.9           # supernova instant (scene-local)
S1_RING_DUR = 4.2
S1_DOLLY = 0.016         # zoom speed of hero layer


def s1_scale(t):
    return 1.0 + S1_DOLLY * max(t, 0.0)


def scene_at(t):
    for i, s in enumerate(SCENES):
        if t < s["t1"] or i == len(SCENES) - 1:
            return i
    return len(SCENES) - 1

# ---------------------------------------------------------------- S2 sun
S2_SUN_C = (-0.80, 0.03)
S2_RS = 0.64
S2_LINE_Y = -0.06
S2_EARTH = (0.64, -0.06)
S2_RE = 0.052
S2_LAUNCH = 1.7
S2_ARRIVE = 8.1
S2_TOTAL_SEC = 499.0  # 8 min 19 s
S2_LIMB_X = S2_SUN_C[0] + (S2_RS ** 2 - (S2_LINE_Y - S2_SUN_C[1]) ** 2) ** 0.5
S2_EDGE_X = S2_EARTH[0] - S2_RE

# ---------------------------------------------------------------- S3 storm
S3_YH = 0.05              # horizon (uv)
S3_STRIKE = 2.0           # main lightning instant (scene-local)
S3_DELAY = 3.0            # thunder delay
S3_BOLT_X = 0.30
S3_BOLT_BASE_ZW = 14.0

# ---------------------------------------------------------------- S4 neuro
S4_T0 = 1.0            # signal leaves the fingertip
S4_V = 4.5             # signal speed along fibres (world units / s)
S4_D0 = -3.0           # front starts here
S4_ARRIVE = 4.55       # front reaches brain tree (D = S4_AXON_LEN)
S4_FOCAL = 2.0
S4_CAMD = 9.0

# ---------------------------------------------------------------- S5 paper
S5_C = (0.30, 0.0)        # diagram centre in uv
S5_R0 = 0.44              # outer radius where streams enter
S5_RD = 0.058             # centre disc radius
# per stream: (phi0, dir, turns(rad), t0, t1, label)
S5_STREAMS = [
    (2.55, 1.0, 1.15 * 3.14159, 1.0, 2.5, "0.1 s"),       # nerve
    (5.35, -1.0, 1.45 * 3.14159, 1.1, 3.5, "3 s"),        # thunder
    (0.65, 1.0, 1.75 * 3.14159, 1.1, 4.6, "8 min"),       # sun
    (3.95, -1.0, 2.05 * 3.14159, 1.2, 5.8, "430 yrs"),    # stars
]
S5_INKS_SRGB = [(0.07, 0.74, 0.64), (0.44, 0.38, 0.97), (1.0, 0.52, 0.12), (0.13, 0.19, 0.60)]
S5_INKS = [tuple(c ** 2.2 for c in k) for k in S5_INKS_SRGB]
S5_GOLD_T = 6.55

# ---------------------------------------------------------------- S6 reach
S6_ORB_L = (-0.52, 0.065)
S6_ORB_R = (0.52, 0.065)
S6_YH = -0.115
S6_T_REACH = 1.7       # first thread leaves
S6_T_ARRIVE = 4.7      # first thread reaches the other side
S6_T_ANSWER = 4.9      # answer leaves
S6_T_MEET = 7.6        # answer reaches origin -> climax
S6_TITLE = 9.9
