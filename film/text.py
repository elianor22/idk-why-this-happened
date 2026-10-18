"""CPU text layers (PIL + raqm): per-glyph animation, sub-pixel placement, defocus blur."""
import numpy as np
from PIL import Image, ImageFont, ImageFilter

FONT_DIR = "/usr/share/fonts/redhat/"
FONTS = {
    "light": FONT_DIR + "RedHatDisplay-Light.otf",
    "reg": FONT_DIR + "RedHatDisplay-Regular.otf",
    "med": FONT_DIR + "RedHatDisplay-Medium.otf",
    "semi": FONT_DIR + "RedHatDisplay-SemiBold.otf",
    "bold": FONT_DIR + "RedHatDisplay-Bold.otf",
    "serif_i": "/usr/share/fonts/google-noto/NotoSerif-LightItalic.ttf",
    "serif": "/usr/share/fonts/google-noto/NotoSerif-Light.ttf",
    "mono": "/usr/share/fonts/adobe-source-code-pro-fonts/SourceCodePro-Regular.otf",
    "mono_l": "/usr/share/fonts/adobe-source-code-pro-fonts/SourceCodePro-Light.otf",
}
SS = 4  # glyph supersampling for sub-pixel positioning

_font_cache = {}
_glyph_cache = {}


def font(name, size):
    k = (name, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(FONTS[name], size, layout_engine=ImageFont.Layout.RAQM)
    return _font_cache[k]


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return 0.5 - 0.5 * np.cos(np.pi * x)


def layout(text, fname, size, tracking=0.0):
    """glyph x offsets (kerned) and total width; tracking in em."""
    f4 = font(fname, size * SS)
    xs = []
    for i in range(len(text)):
        xs.append((f4.getlength(text[:i], features=["kern"]) if i else 0.0) / SS + tracking * size * i)
    total = f4.getlength(text, features=["kern"]) / SS + tracking * size * max(len(text) - 1, 0)
    return xs, total


def glyph_mask(ch, fname, size, fx, fy):
    """L-mode coverage of ch drawn with fractional offset (fx, fy) in px. returns (arr, ox, oy)
    arr[0,0] sits at integer pixel (ox, oy) relative to the glyph origin (left, baseline-top)."""
    key = (ch, fname, size, int(fx * SS) % SS, int(fy * SS) % SS)
    g = _glyph_cache.get(key)
    if g is not None:
        return g
    f4 = font(fname, size * SS)
    pad = int(size * 0.45)
    adv = int(f4.getlength(ch) / SS) + 1
    bw, bh = (adv + 2 * pad), int(size * 1.7) + 2 * pad
    big = Image.new("L", (bw * SS, bh * SS), 0)
    from PIL import ImageDraw
    d = ImageDraw.Draw(big)
    d.text((pad * SS + key[3], pad * SS + key[4]), ch, font=f4, fill=255, anchor="ls" if False else "la")
    small = big.resize((bw, bh), Image.BOX)
    arr = np.asarray(small, dtype=np.float32) / 255.0
    g = (arr, -pad, -pad)
    _glyph_cache[key] = g
    return g


class Layer:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.buf = np.zeros((h, w, 4), np.float32)  # premultiplied RGBA

    def clear(self):
        self.buf[:] = 0

    def blit(self, mask, x, y, color, alpha):
        h, w = mask.shape
        x0, y0 = int(x), int(y)
        x1, y1 = x0 + w, y0 + h
        cx0, cy0 = max(x0, 0), max(y0, 0)
        cx1, cy1 = min(x1, self.w), min(y1, self.h)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        m = mask[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0] * alpha
        dst = self.buf[cy0:cy1, cx0:cx1]
        inv = 1.0 - m[..., None]
        dst[..., :3] = dst[..., :3] * inv + m[..., None] * np.asarray(color, np.float32)
        dst[..., 3] = dst[..., 3] * inv[..., 0] + m

    def glyph(self, ch, fname, size, x, y, color, alpha=1.0, blur=0.0, scale=1.0):
        """x = left origin, y = top of the em box (PIL 'la' anchor)."""
        if alpha <= 0.002 or ch == " ":
            return
        fx, fy = x - np.floor(x), y - np.floor(y)
        arr, ox, oy = glyph_mask(ch, fname, size, fx, fy)
        if scale != 1.0:
            im = Image.fromarray((arr * 255).astype(np.uint8))
            nw, nh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
            im = im.resize((nw, nh), Image.BICUBIC)
            # keep scaling about glyph centre
            ox = ox + (arr.shape[1] - nw) // 2
            oy = oy + (arr.shape[0] - nh) // 2
            arr = np.asarray(im, np.float32) / 255.0
        if blur > 0.3:
            im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
            im = im.filter(ImageFilter.GaussianBlur(float(blur)))
            arr = np.asarray(im, np.float32) / 255.0
            # energy compensation so blurred glyphs stay readable but softer
            arr = arr * (1.0 + 0.0 * blur)
        self.blit(arr, np.floor(x) + ox, np.floor(y) + oy, color, alpha)

    def text(self, s, fname, size, x, y, color, tracking=0.0, align="l", alpha=1.0, blur=0.0):
        xs, total = layout(s, fname, size, tracking)
        if align == "c":
            x -= total / 2
        elif align == "r":
            x -= total
        for ch, gx in zip(s, xs):
            self.glyph(ch, fname, size, x + gx, y, color, alpha, blur)
        return total

    def anim_text(self, s, fname, size, x, y, color, t, t_in, dur_in=0.9, stagger=0.045,
                  t_out=None, dur_out=0.7, tracking=0.0, align="l", rise=26.0, blur_amt=16.0,
                  alpha=1.0, word_stagger=None, drift_out=-18.0, grow=0.0):
        """Per-glyph reveal: fade + defocus + rise, staggered; reverse on exit."""
        xs, total = layout(s, fname, size, tracking)
        if align == "c":
            x -= total / 2
        elif align == "r":
            x -= total
        n = len(s)
        # optional word-based stagger index
        idx = []
        if word_stagger is not None:
            w = 0
            for ch in s:
                idx.append(w)
                if ch == " ":
                    w += 1
        for i, (ch, gx) in enumerate(zip(s, xs)):
            if word_stagger is not None:
                delay = idx[i] * word_stagger + (i * stagger * 0.25)
            else:
                delay = i * stagger
            p = ease_out((t - t_in - delay) / dur_in)
            a = smooth((t - t_in - delay) / (dur_in * 0.8))
            yo = (1 - p) * rise
            bl = (1 - p) ** 2 * blur_amt
            sc = 1.0
            if t_out is not None:
                q = ease_io((t - t_out - delay * 0.6) / dur_out)
                a *= 1 - q
                yo += q * drift_out
                bl += q * q * blur_amt * 0.8
            if grow:
                sc = 1.0 + grow * (1 - p)
            self.glyph(ch, fname, size, x + gx, y + yo, color, a * alpha, bl, sc)
        return total
