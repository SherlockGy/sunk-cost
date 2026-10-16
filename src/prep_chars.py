# 角色与道具抠图：纯色背景转透明；同一组动作帧用同一个裁切框，保证帧间对齐；
# 记录每张图的脚底锚点、身高和背包位置（红色区域），供场景摆放和挂标签
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "assets" / "chars_raw"
CUT = ROOT / "assets" / "chars"
LOG = "[prep_chars 角色抠图]"

MAGENTA = {"prop_teashop", "prop_exit", "scene_buffet", "scene_buffet_b"}
# 一张图里有多个独立物体，按连通区域拆开：原图名 -> 拆分后的前缀
SPLIT = {"crowd": "crowd", "items": "item"}  # items 拆出 item_0（小票）、item_1（电影票）
# 动作帧分组：组内共用裁切框
GROUPS = {
    # 同一张门面图的两个姿势：共用裁切框，切换时背景不跳
    "scene_buffet": ["scene_buffet", "scene_buffet_b"],
}


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def key_alpha(rgb, key):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    k = g - np.maximum(r, b) if key == "green" else np.minimum(r, b) - g
    strong = k > 70
    lab, _ = ndimage.label(strong)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bg = np.isin(lab, border[border > 0])
    bg |= k > 190
    band = ndimage.binary_dilation(bg, iterations=4)
    alpha = np.ones(k.shape, np.float32)
    soft = 1 - smoothstep(25, 150, k)
    alpha[band] = soft[band]
    alpha[bg] = 0.0
    out = rgb.copy()
    edge = band & (alpha > 0)
    if key == "green":
        out[..., 1] = np.where(edge, np.minimum(g, np.maximum(r, b) + 8), g)
    else:
        lim = g + 8
        out[..., 0] = np.where(edge, np.minimum(r, lim), r)
        out[..., 2] = np.where(edge, np.minimum(b, lim), b)
    # 去掉孤立的小噪点
    lab2, n = ndimage.label(alpha > 0.5)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(alpha), lab2, range(1, n + 1))
        keep = np.isin(lab2, 1 + np.where(sizes > 0.002 * alpha.size)[0])
        alpha = np.where(keep | (alpha < 0.5), alpha, 0)
        alpha[~ndimage.binary_dilation(keep, iterations=3)] = 0
    return out, alpha


def load(name):
    key = "magenta" if name in MAGENTA else "green"
    rgb = np.array(Image.open(RAW / f"{name}.png").convert("RGB")).astype(np.float32)
    out, a = key_alpha(rgb, key)
    return out, a


def bbox(a):
    ys, xs = np.where(a > 0.3)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def bag_box(rgb, a):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    m = (r > 170) & (g < 130) & (b < 110) & (a > 0.5)
    lab, n = ndimage.label(m)
    if n == 0:
        return None
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    big = 1 + int(np.argmax(sizes))
    if sizes[big - 1] < 2000:
        return None
    ys, xs = np.where(lab == big)
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def save(name, rgb, a, box, meta):
    x0, y0, x1, y1 = box
    pad = 6
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(a.shape[1], x1 + pad), min(a.shape[0], y1 + pad)
    crop_rgb, crop_a = rgb[y0:y1, x0:x1], a[y0:y1, x0:x1]
    img = np.dstack([np.clip(crop_rgb, 0, 255), np.clip(crop_a, 0, 1) * 255]).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(CUT / f"{name}.png")
    own = bbox(crop_a)
    # 脚底锚点：不透明像素最底部一行的水平中点
    ys, xs = np.where(crop_a > 0.5)
    bottom = ys.max()
    feet = xs[ys >= bottom - 12]
    bb = bag_box(crop_rgb, crop_a)
    meta[name] = dict(w=int(x1 - x0), h=int(y1 - y0), foot=[float(feet.mean()), float(bottom)],
                      top=float(own[1]), height=float(bottom - own[1]), bag=bb,
                      crop=[int(x0), int(y0)])  # 裁切偏移：原图坐标减去它就是裁切后坐标


def main(names=None):
    CUT.mkdir(parents=True, exist_ok=True)
    meta_path = CUT / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    avail = {p.stem for p in RAW.glob("*.png")}
    grouped = set()
    for gname, members in GROUPS.items():
        members = [m for m in members if m in avail]
        if not members or (names and not set(members) & set(names)):
            grouped |= set(members)
            continue
        data = {m: load(m) for m in members}
        boxes = [bbox(a) for _, a in data.values()]
        union = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
        for m, (rgb, a) in data.items():
            save(m, rgb, a, union, meta)
            print(f"{LOG}[{m}] 组 {gname}", flush=True)
        grouped |= set(members)
    # 路人群像、物件：按连通区域拆成单个
    for src, prefix in SPLIT.items():
        if src not in avail or (names and src not in names):
            grouped.add(src)
            continue
        rgb, a = load(src)
        lab, n = ndimage.label(ndimage.binary_dilation(a > 0.5, iterations=6))
        comps = []
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            if len(xs) > 0.004 * a.size:
                comps.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1, i))
        comps.sort()
        for j, (x0, y0, x1, y1, i) in enumerate(comps):
            aj = np.where(lab == i, a, 0)
            save(f"{prefix}_{j}", rgb, aj, (x0, y0, x1, y1), meta)
            print(f"{LOG}[{prefix}_{j}]", flush=True)
        grouped.add(src)
    for name in sorted(avail - grouped):
        if names and name not in names:
            continue
        rgb, a = load(name)
        save(name, rgb, a, bbox(a), meta)
        print(f"{LOG}[{name}]", flush=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
