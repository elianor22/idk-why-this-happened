import sys, os, time, argparse, subprocess
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import *
from engine import Engine
from text import Layer
import scenes as S


def lerp(a, b, m):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * m for x, y in zip(a, b))
    return a + (b - a) * m


class Renderer:
    def __init__(self):
        self.eng = Engine(W, H)
        self.main = Layer(W, H)
        self.hud = Layer(W, H)
        self.objs = [S.SCENE_OBJS.get(s["name"]) for s in SCENES]

    def frame(self, t, fi):
        eng = self.eng
        i = scene_at(t)
        A = self.objs[i]
        sA = SCENES[i]
        mode, m, other = 0, 0.0, None
        # transition window?
        for k in range(len(SCENES) - 1):
            T = SCENES[k]["t1"]
            hw = TRANS_HW[k]
            if T - hw <= t < T + hw:
                i = k
                A, other = self.objs[k], self.objs[k + 1]
                m = (t - (T - hw)) / (2 * hw)
                mode = S.TRANS_MODE[k]
                break
        A_idx = i
        tA = t - SCENES[A_idx]["t0"]
        A.render(eng, eng.hdr["A"][1], tA, fi)
        gA = A.grade(tA)
        if other is not None:
            B_idx = A_idx + 1
            tB = t - SCENES[B_idx]["t0"]
            other.render(eng, eng.hdr["B"][1], tB, fi)
            gB = other.grade(tB)
            g = {k: lerp(gA[k], gB[k], m) if k in gB else gA[k] for k in gA}
            gain_main = lerp(A.gain_main, other.gain_main, m)
            gain_hud = lerp(A.gain_hud, other.gain_hud, m)
        else:
            g = gA
            gain_main, gain_hud = A.gain_main, A.gain_hud
        # text
        self.main.clear(); self.hud.clear()
        A.text(tA, self.main, self.hud)
        if other is not None:
            other.text(tB, self.main, self.hud)
        eng.upload_text("main", self.main)
        eng.upload_text("hud", self.hud)
        # mix
        eng.pass_("mix.frag", eng.hdr["M"][1],
                  {"uA": eng.hdr["A"][0], "uB": eng.hdr["B"][0], "uTxtMain": eng.txt["main"], "uTxtHud": eng.txt["hud"]},
                  uGainMain=gain_main, uGainHud=gain_hud, uMode=mode, uM=m, uIrisC=(0.5, 0.5))
        bl = eng.bloom(eng.hdr["M"][0], g["bloom_thresh"])
        st = eng.streak_pass()
        eng.pass_("composite.frag", eng.out_fbo,
                  {"uHdr": eng.hdr["M"][0], "uBloom": bl, "uStreak": st},
                  uFrame=fi, uExposure=g["exposure"], uContrast=g["contrast"], uSat=g["sat"],
                  uLift=g["lift"], uGain=g["gain"], uShadowTint=g["shadow"], uHighTint=g["high"],
                  uBloomAmt=g["bloom"], uStreakAmt=g["streak"], uStreakTint=g["streak_tint"],
                  uVig=g["vig"], uCA=g["ca"], uGrain=g["grain"], uTone=g["tone"], uFade=g["fade"])
        return eng.read_frame()


def to_png(buf, path):
    im = Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, -1)
    im.save(path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["still", "video"])
    ap.add_argument("--t", type=float, nargs="+", default=[1.0])
    ap.add_argument("--out", default="out/still.png")
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--crf", type=int, default=0)
    ap.add_argument("--step", type=int, default=1)
    a = ap.parse_args()
    r = Renderer()
    if a.cmd == "video":
        f0 = int(round(a.start * FPS))
        f1 = int(round((a.end if a.end is not None else TOTAL) * FPS))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-framerate", str(FPS), "-i", "-", "-vf", "vflip", "-c:v", "ffv1", "-level", "3", "-g", "1", a.out]
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        t_start = time.time()
        for fi in range(f0, f1, a.step):
            buf = r.frame(fi / FPS, fi)
            pr.stdin.write(buf)
            if (fi - f0) % 30 == 0:
                el = time.time() - t_start
                done = (fi - f0) / max(a.step, 1) + 1
                eta = el / done * ((f1 - f0) / a.step - done)
                print(f"frame {fi}/{f1}  t={fi/FPS:6.2f}s  elapsed {el:6.0f}s  eta {eta:6.0f}s", flush=True)
        pr.stdin.close()
        pr.wait()
        print("done", a.out, time.time() - t_start)
        sys.exit(0)
    if a.cmd == "still":
        for t in a.t:
            t0 = time.time()
            buf = r.frame(t, int(t * FPS))
            p = a.out if len(a.t) == 1 else a.out.replace(".png", f"_{t:06.2f}.png")
            to_png(buf, p)
            print(p, f"{time.time()-t0:.2f}s")
