# 平面海报风格的绘图工具：配色、动画曲线、逐字动画、图标（硬币、门、时钟、标签、卡片、气泡、曲线图）
import math

import numpy as np
import skia

from draw_util import font

W, H = 1920, 1080
INK = (0.106, 0.165, 0.255)
NAVY = (0.075, 0.11, 0.19)
CREAM = (0.953, 0.918, 0.847)
PAPER = (0.98, 0.96, 0.91)
RED = (0.886, 0.318, 0.227)
MUSTARD = (0.914, 0.706, 0.298)
TEAL = (0.149, 0.49, 0.455)
GREY = (0.6, 0.6, 0.62)
DUSK = (0.33, 0.31, 0.45)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease_out(x, p=3):
    x = clamp(x)
    return 1 - (1 - x) ** p


def ease_in_out(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def back(x, s=1.9):
    """带回弹的出现（略微超过再回落）"""
    x = clamp(x)
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def ramp(t, a, b, fn=ease_in_out):
    if b <= a:
        return 1.0 if t >= b else 0.0
    return fn(clamp((t - a) / (b - a)))


def lerp(a, b, k):
    if isinstance(a, tuple):
        return tuple(x + (y - x) * k for x, y in zip(a, b))
    return a + (b - a) * k


def P(c, a=1.0):
    return skia.Paint(AntiAlias=True, Color=skia.Color4f(*c, clamp(a)))


def stroke(c, w, a=1.0, cap=True):
    p = skia.Paint(AntiAlias=True, Color=skia.Color4f(*c, clamp(a)), Style=skia.Paint.kStroke_Style, StrokeWidth=w)
    if cap:
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def rrect(c, x, y, w, h, r, paint):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), paint)


def text_width(s, f, spacing=0.0):
    return sum(f.measureText(ch) for ch in s) + spacing * (len(s) - 1)


def text(c, s, x, y, f, color, align="left", a=1.0, spacing=0.0):
    total = text_width(s, f, spacing)
    x0 = x - (total / 2 if align == "center" else total if align == "right" else 0)
    for ch in s:
        c.drawString(ch, x0, y, f, P(color, a))
        x0 += f.measureText(ch) + spacing
    return total


def anim_text(c, s, x, y, f, color, t, t0, align="left", spacing=0.0, stagger=0.035, dur=0.32, style="pop", a=1.0,
              t_out=None, out_dur=0.25):
    """逐字出现：pop 弹出 / rise 上浮 / slam 从大到小砸下"""
    if t < t0:
        return
    total = text_width(s, f, spacing)
    x0 = x - (total / 2 if align == "center" else total if align == "right" else 0)
    fa = 1.0
    if t_out is not None:
        fa = 1 - ramp(t, t_out, t_out + out_dur)
        if fa <= 0:
            return
    size = f.getSize()
    for i, ch in enumerate(s):
        wd = f.measureText(ch)
        k = (t - t0 - i * stagger) / dur
        if k <= 0:
            x0 += wd + spacing
            continue
        if style == "pop":
            sc = back(k)
            dy = 0
            al = clamp(k * 3)
        elif style == "rise":
            sc = 1.0
            dy = (1 - ease_out(k)) * size * 0.35
            al = ease_out(k)
        else:  # slam
            sc = 1 + 0.9 * (1 - ease_out(k, 4))
            dy = 0
            al = clamp(k * 4)
        c.save()
        cx, cy = x0 + wd / 2, y - size * 0.35
        c.translate(cx, cy + dy)
        c.scale(sc, sc)
        c.translate(-cx, -cy)
        c.drawString(ch, x0, y, f, P(color, al * fa * a))
        c.restore()
        x0 += wd + spacing


def strike(c, x0, x1, y, color, t, t0, dur=0.3, width=7):
    k = ramp(t, t0, t0 + dur, ease_out)
    if k > 0:
        c.drawLine(x0, y, x0 + (x1 - x0) * k, y, stroke(color, width))


def coin(c, x, y, r, label, color=MUSTARD, ink=INK, a=1.0):
    c.drawCircle(x, y, r, P(color, a))
    c.drawCircle(x, y, r * 0.8, stroke((1, 1, 1), r * 0.06, 0.45 * a))
    f = font("serif", r * (0.62 if len(label) <= 3 else 0.5), 900)
    text(c, label, x, y + r * 0.22, f, ink, align="center", a=a)


def tag(c, x, y, label, size=30, color=PAPER, ink=INK, a=1.0, rot=0.0, string_to=None):
    """行李牌样式的标签；string_to 给出绳子另一端（画布坐标）"""
    f = font("sans", size, 800)
    wd = f.measureText(label)
    w, h = wd + size * 0.9, size * 1.55
    if string_to is not None:
        c.drawLine(string_to[0], string_to[1], x, y - h / 2, stroke(ink, 2.5, 0.8 * a))
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    rrect(c, -w / 2, -h / 2, w, h, size * 0.25, P(color, a))
    c.drawCircle(-w / 2 + size * 0.32, 0, size * 0.1, P(ink, 0.6 * a))
    c.drawString(label, -wd / 2 + size * 0.15, size * 0.36, f, P(ink, a))
    c.restore()
    return w, h


def door(c, x, y, w, h, label, color, a=1.0, open_k=0.0):
    rrect(c, x, y, w, h, 10, P(INK, 0.35 * a))
    # 门板（开门时变窄，像向里打开）
    ww = w * (1 - 0.65 * open_k)
    rrect(c, x, y, ww, h, 10, P(color, a))
    c.drawCircle(x + ww - 22, y + h * 0.55, 8, P(PAPER, 0.9 * a))
    f = font("serif", 46, 900)
    text(c, label, x + w / 2, y - 26, f, PAPER, align="center", a=a)


def clock_digits(c, x, y, minutes, size, color, a=1.0):
    f = font("mono", size)
    mm = int(minutes)
    ss = int((minutes - mm) * 60)
    text(c, f"{mm:02d}:{ss:02d}", x, y, f, color, align="center", a=a)


def bubble(c, x, y, w, h, tail_x, tail_y, color=PAPER, a=1.0):
    path = skia.Path()
    path.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 36, 36))
    tail = skia.Path()
    tail.moveTo(x + w * 0.22, y + h - 4)
    tail.lineTo(tail_x, tail_y)
    tail.lineTo(x + w * 0.36, y + h - 4)
    tail.close()
    c.drawPath(path, P(color, a))
    c.drawPath(tail, P(color, a))


def glow(c, x, y, r, color=(1.0, 0.92, 0.7), a=1.0):
    g = skia.GradientShader.MakeRadial(skia.Point(x, y), r, [skia.Color4f(*color, 0.85 * a).toColor(),
                                                             skia.Color4f(*color, 0).toColor()])
    c.drawCircle(x, y, r, skia.Paint(AntiAlias=True, Shader=g))


def vgrad(c, top, bottom, y0=0, y1=H, mid=None):
    cols = [skia.Color4f(*top, 1).toColor()]
    pos = [0.0]
    if mid:
        cols.append(skia.Color4f(*mid[0], 1).toColor())
        pos.append(mid[1])
    cols.append(skia.Color4f(*bottom, 1).toColor())
    pos.append(1.0)
    sh = skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, y1)], cols, pos)
    c.drawRect(skia.Rect.MakeXYWH(0, y0, W, y1 - y0), skia.Paint(Shader=sh))


class Grain:
    """预先生成几张噪点，逐帧轮换，给平面画面加一点胶片质感"""

    def __init__(self, n=6, amt=6.0):
        rng = np.random.default_rng(9)
        self.frames = [rng.normal(0, amt, (H, W, 1)).astype(np.float32) for _ in range(n)]

    def apply(self, rgb, frame):
        out = rgb.astype(np.float32) + self.frames[frame % len(self.frames)]
        return np.clip(out, 0, 255).astype(np.uint8)
