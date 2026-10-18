"""moderngl engine: fullscreen passes, HDR targets, bloom chain, composite, text upload."""
import os
import re
import numpy as np
import moderngl

HERE = os.path.dirname(os.path.abspath(__file__))
SHADERS = os.path.join(HERE, "shaders")


def read_shader(name):
    with open(os.path.join(SHADERS, name)) as f:
        return f.read()


def build_frag(name):
    """`#include name` lines are expanded; common.glsl auto-included after #version."""
    src = read_shader(name)

    def inc(m):
        return read_shader(m.group(1))

    src = re.sub(r"^\s*#include\s+(\S+)\s*$", inc, src, flags=re.M)
    return src


class Engine:
    def __init__(self, w=1920, h=1080):
        self.w, self.h = w, h
        self.ctx = moderngl.create_standalone_context(backend="egl", require=430)
        ctx = self.ctx
        self.quad = ctx.buffer(np.array([-1, -1, 3, -1, -1, 3], "f4").tobytes())
        self.progs = {}
        self.vaos = {}
        self.vert_src = read_shader("fs.vert")
        # HDR targets
        self.hdr = {}
        for k in ("A", "B", "M"):
            self.hdr[k] = self._target(w, h)
        # bloom chain
        self.levels = 6
        self.down, self.up = [], []
        sw, sh = w, h
        for i in range(self.levels):
            sw, sh = max(sw // 2, 1), max(sh // 2, 1)
            self.down.append(self._target(sw, sh))
            self.up.append(self._target(sw, sh))
        sw4, sh4 = self.down[1][0].size
        self.streak = self._target(sw4, sh4)
        # text layers
        self.txt = {}
        for k in ("main", "hud"):
            t = ctx.texture((w, h), 4, dtype="f1")
            t.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self.txt[k] = t
        # output
        self.out_tex = ctx.texture((w, h), 3, dtype="f1")
        self.out_fbo = ctx.framebuffer(color_attachments=[self.out_tex])
        self.black = self._target(4, 4)
        self.black[1].use()
        self.black[1].clear(0, 0, 0, 1)

    def _target(self, w, h):
        tex = self.ctx.texture((w, h), 4, dtype="f2")
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        tex.repeat_x = tex.repeat_y = False
        fbo = self.ctx.framebuffer(color_attachments=[tex])
        return tex, fbo

    # ------------------------------------------------------------ programs
    def program(self, frag, vert=None):
        key = (frag, vert)
        if key not in self.progs:
            fsrc = build_frag(frag)
            # inject common after #version line
            if "common.glsl" not in fsrc and frag not in ("mix.frag", "composite.frag", "bloom_down.frag",
                                                         "bloom_up.frag", "streak.frag"):
                lines = fsrc.split("\n", 1)
                fsrc = lines[0] + "\n" + read_shader("common.glsl") + "\n" + lines[1]
            vsrc = self.vert_src if vert is None else build_frag(vert)
            prog = self.ctx.program(vertex_shader=vsrc, fragment_shader=fsrc)
            self.progs[key] = prog
            if vert is None:
                self.vaos[key] = self.ctx.vertex_array(prog, [(self.quad, "2f", "p")])
        return self.progs[key]

    def set(self, prog, **u):
        for k, v in u.items():
            try:
                m = prog[k]
            except KeyError:
                continue
            if isinstance(v, (list, tuple, np.ndarray)):
                arr = np.asarray(v, "f4")
                if arr.ndim > 1 or m.array_length > 1:
                    m.write(arr.tobytes())
                else:
                    m.value = tuple(arr.tolist())
            else:
                m.value = v

    def pass_(self, frag, fbo, textures=None, **u):
        prog = self.program(frag)
        textures = textures or {}
        unit = 0
        for name, tex in textures.items():
            tex.use(unit)
            try:
                prog[name].value = unit
            except KeyError:
                pass
            unit += 1
        fbo.use()
        self.ctx.viewport = (0, 0, fbo.size[0], fbo.size[1])
        self.set(prog, uRes=tuple(map(float, fbo.size)), **u)
        self.vaos[(frag, None)].render(moderngl.TRIANGLES, vertices=3)

    # ------------------------------------------------------------ bloom
    def bloom(self, src_tex, thresh=0.0):
        self.pass_("bloom_down.frag", self.down[0][1], {"uTex": src_tex},
                   uTexel=(1.0 / self.w, 1.0 / self.h), uFirst=1, uThresh=thresh)
        for i in range(1, self.levels):
            prev = self.down[i - 1][0]
            self.pass_("bloom_down.frag", self.down[i][1], {"uTex": prev},
                       uTexel=(1.0 / prev.size[0], 1.0 / prev.size[1]), uFirst=0, uThresh=0.0)
        # up chain: up[last] = down[last]
        last = self.levels - 1
        self.ctx.copy_framebuffer(self.up[last][1], self.down[last][1])
        weights = [1.0, 1.0, 1.0, 1.0, 1.0]
        for i in range(last - 1, -1, -1):
            low = self.up[i + 1][0]
            self.pass_("bloom_up.frag", self.up[i][1], {"uLow": low, "uCur": self.down[i][0]},
                       uLowTexel=(1.0 / low.size[0], 1.0 / low.size[1]), uW=weights[i])
        return self.up[0][0]

    def streak_pass(self):
        src = self.down[1][0]
        self.pass_("streak.frag", self.streak[1], {"uTex": src}, uTexel=(1.0 / src.size[0], 1.0 / src.size[1]))
        return self.streak[0]

    # ------------------------------------------------------------ text
    def upload_text(self, key, layer):
        a = np.clip(layer.buf, 0.0, 1.0)
        data = (a * 255.0 + 0.5).astype(np.uint8)
        self.txt[key].write(data.tobytes())

    def read_frame(self):
        return self.out_fbo.read(components=3)
