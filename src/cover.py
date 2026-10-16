# 封面：放下背包、手握“答案”、迎着日出；横版与竖版
import numpy as np
import skia
from PIL import Image

import sprites
from draw_util import font, surface, to_array
from gfx import RED, P, glow, rrect, text, vgrad
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "out"


def scene(w, h, title_y, sub_y, fig_x, fig_h, ground, title_size):
    s = surface(w, h)
    c = s.getCanvas()
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, ground)],
                                        [skia.Color4f(0.09, 0.08, 0.2, 1).toColor(), skia.Color4f(0.62, 0.34, 0.42, 1).toColor(),
                                         skia.Color4f(1.0, 0.68, 0.42, 1).toColor()], [0.0, 0.6, 1.0])
    c.drawRect(skia.Rect.MakeWH(w, ground), skia.Paint(Shader=sh))
    sun_x = w * 0.78
    glow(c, sun_x, ground + 20, w * 0.38, (1, 0.88, 0.62), a=0.95)
    c.drawCircle(sun_x, ground + 20, w * 0.055, P((1, 0.94, 0.78)))
    c.drawRect(skia.Rect.MakeXYWH(0, ground, w, h - ground), P((0.17, 0.12, 0.2)))
    # 放下的背包与手握答案卡的主角（codex 生成的角色帧）
    sprites.draw(c, "backpack_full", fig_x - fig_h * 0.45, ground + 6, fig_h * 0.42)
    sprites.draw(c, "her_card", fig_x, ground + 4, fig_h)
    glow(c, fig_x + fig_h * 0.17, ground - fig_h * 0.62, fig_h * 0.35, a=0.6)

    def title(s_, y, size, color, weight=900, spacing=0.0):
        f = font("serif", size, weight)
        sp = P((0.05, 0.03, 0.08), 0.6)
        sp.setImageFilter(skia.ImageFilters.Blur(size * 0.12, size * 0.12))
        wd = sum(f.measureText(ch) for ch in s_) + spacing * (len(s_) - 1)
        x = w / 2 - wd / 2
        for ch in s_:
            c.drawString(ch, x, y + size * 0.04, f, sp)
            c.drawString(ch, x, y, f, P(color))
            x += f.measureText(ch) + spacing

    title("沉没成本", title_y, title_size, (1, 0.97, 0.92), spacing=title_size * 0.15)
    title("为什么，你应该放下它", sub_y, title_size * 0.36, (1.0, 0.82, 0.5), weight=800, spacing=title_size * 0.04)
    return to_array(s)[..., :3]


def main():
    # 输出目录不存在时先建好（新克隆的仓库里没有 out/）
    (OUT / "preview").mkdir(parents=True, exist_ok=True)
    a = scene(1920, 1080, 250, 370, 470, 600, 900, 170)
    b = scene(1080, 1920, 420, 540, 470, 780, 1420, 170)
    for name, img in (("cover_16x9", a), ("cover_9x16", b)):
        Image.fromarray(img).save(OUT / f"{name}.png")
        Image.fromarray(img).save(OUT / f"{name}.jpg", quality=93)
    sheet = Image.new("RGB", (960 + 304, 540))
    sheet.paste(Image.fromarray(a).resize((960, 540)), (0, 0))
    sheet.paste(Image.fromarray(b).resize((304, 540)), (960, 0))
    sheet.save(OUT / "preview" / "covers.png")
    print("ok")


if __name__ == "__main__":
    main()
