# 位图角色/道具的摆放：以脚底为锚点，按身高缩放，可翻转、旋转、透明
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import skia
from PIL import Image

CUT = Path(__file__).resolve().parent.parent / "assets" / "chars"
META = json.loads((CUT / "meta.json").read_text(encoding="utf-8")) if (CUT / "meta.json").exists() else {}


@lru_cache(maxsize=64)
def image(name):
    arr = np.array(Image.open(CUT / f"{name}.png").convert("RGBA"))
    return skia.Image.fromarray(arr, colorType=skia.ColorType.kRGBA_8888_ColorType)


def draw(c, name, x, y, height, flip=False, alpha=1.0, rot=0.0, sy=1.0, tint=None):
    """把 name 画在画布上：脚底在 (x, y)，身高 height 像素。返回背包锚点等信息"""
    if name not in META or not (CUT / f"{name}.png").exists():
        return {}
    m = META[name]
    s = height / m["height"]
    fx, fy = m["foot"]
    c.save()
    c.translate(x, y)
    if rot:
        c.rotate(rot)
    c.scale(-s if flip else s, s * sy)
    paint = skia.Paint(AntiAlias=True)
    paint.setAlphaf(alpha)
    if tint is not None:
        paint.setColorFilter(skia.ColorFilters.Blend(skia.Color4f(*tint, 1.0).toColor(), skia.BlendMode.kSrcIn))
    c.drawImageRect(image(name), skia.Rect.MakeXYWH(-fx, -fy, m["w"], m["h"]),
                    skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), paint)
    c.restore()
    out = {"scale": s}
    if m.get("bag"):
        bx0, by0, bx1, by1 = m["bag"]
        # 背包下沿偏后的位置，用来挂标签
        ax = (bx0 + (bx1 - bx0) * 0.35 - fx) * s
        ay = (by1 - fy) * s * sy
        out["bag"] = (x - ax if flip else x + ax, y + ay)
        out["bag_box"] = [(v - fx) * s for v in (bx0, bx1)]
        # 背包中心：物件飞进背包的落点
        cx = ((bx0 + bx1) / 2 - fx) * s
        out["bag_c"] = (x - cx if flip else x + cx, y + ((by0 + by1) / 2 - fy) * s * sy)
    out["top"] = y - m["height"] * s * sy
    return out


def point(name, x, y, height, px, py, flip=False):
    """生成原图上的像素点 (px, py) 在画布上的位置；用于整图场景里手动标定背包等位置"""
    m = META[name]
    px, py = px - m["crop"][0], py - m["crop"][1]
    s = height / m["height"]
    fx, fy = m["foot"]
    dx = (px - fx) * s
    return (x - dx if flip else x + dx, y + (py - fy) * s)


def draw_at(c, name, rx, ry, X, Y, height, **kw):
    """把整图画到画布上，使原图像素点 (rx, ry) 正好落在 (X, Y)；返回把原图坐标换算成画布坐标的函数"""
    m = META[name]
    s = height / m["height"]
    fx, fy = m["foot"]
    x = X - (rx - m["crop"][0] - fx) * s
    y = Y - (ry - m["crop"][1] - fy) * s
    draw(c, name, x, y, height, **kw)
    return lambda px, py: point(name, x, y, height, px, py)
