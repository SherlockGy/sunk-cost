# 分镜：每个镜头是 (开始, 结束, 函数, 是否深色底)；所有动画都是时间的纯函数
import math

import numpy as np
import skia

import sprites
from draw_util import font, surface, to_array
from gfx import (CREAM, DUSK, GREY, H, INK, MUSTARD, NAVY, PAPER, RED, TEAL, W, P, Grain, anim_text, back, bubble,
                 clamp, clock_digits, coin, door, ease_in_out, ease_out, glow, lerp, ramp, rrect, strike, stroke, tag,
                 text, text_width, vgrad)
from timeline import BAR, BEAT, SECTION, T, TEXT, TOTAL, e, s, wt

SEC = SECTION
FLOOR_H = 300


def flash(c, t, t_hit, color=(1, 1, 1), amt=0.22, dur=0.18):
    k = (t - t_hit) / dur
    if 0 <= k < 1:
        c.drawRect(skia.Rect.MakeWH(W, H), P(color, amt * (1 - k)))
SERIF = lambda size, w=900: font("serif", size, w)
SANS = lambda size, w=700: font("sans", size, w)

# 四个沉没成本的具体物件（占位、精灵名、显示高度、对应的代价）：小票、电影票、计时器、合照
ITEMS = [(None, "item_0", 150, "¥198"), (None, "item_1", 95, "2小时"), (None, "item_timer", 120, "40分钟"),
         (None, "item_photo", 130, "7年")]


def cam(c, t, t0, t1, zoom=0.04, cx=W / 2, cy=H / 2):
    k = ramp(t, t0, t1, lambda x: x)
    z = 1 + zoom * k
    c.translate(cx, cy)
    c.scale(z, z)
    c.translate(-cx, -cy)


def hit_shake(t, t_hit, amp=10):
    k = t - t_hit
    if k < 0 or k > 0.35:
        return 0.0
    return amp * math.exp(-k * 12) * math.sin(k * 60)


def big_number(c, t, t0, num, color, x=200, y=430):
    k = (t - t0) / 0.35
    if k <= 0:
        return
    sc = 1 + 1.2 * (1 - ease_out(k, 4))
    c.save()
    c.translate(x + 110, y - 160)
    c.scale(sc, sc)
    c.translate(-(x + 110), -(y - 160))
    text(c, num, x, y, SERIF(380), color, a=clamp(k * 3))
    c.restore()


# 弯腰背鼓包的图与站直的图同一身材时的高度比（对比头和鞋的大小得出）
HEAVY_K = 0.85


def her(c, kind, x, y, h, t, flip=False, alpha=1.0):
    """主角：带轻微呼吸；h 一律是站直时的身高"""
    sy = 1 + 0.007 * math.sin(t * 1.7)
    if kind == "heavy":
        # 背着装满沉没成本的鼓包：呼吸更沉、更慢
        name, sy = "her_heavy", 1 + 0.01 * math.sin(t * 1.2)
        h *= HEAVY_K
    else:
        name = f"her_{kind}"
    return sprites.draw(c, name, x, y, h, flip=flip, alpha=alpha, sy=sy)


def window_k(t, a, b, f=0.2):
    return ramp(t, a - f, a) * (1 - ramp(t, b, b + f))


# ================================================================ 起：四个熟悉的“舍不得”
def shot_buffet(c, t):
    t0 = 0.0
    c.clear(skia.Color4f(*CREAM, 1).toColor())
    cam(c, t, t0, s("H02"), 0.05, 1350, 600)
    c.drawRect(skia.Rect.MakeXYWH(0, 900, W, 180), P((0.91, 0.86, 0.77)))
    # 整图：吃撑了靠着餐厅门口的墙柱歇一下（人和墙一起生成，接触是对的）
    c.drawOval(skia.Rect.MakeXYWH(1110, 925, 700, 40), P((0.7, 0.62, 0.52), 0.35))
    # 说到“扶着墙”时从刚出门切到整个人靠在墙上
    slump = t > wt("H01", "扶着墙") - 0.1
    to = sprites.draw_at(c, "scene_buffet_b" if slump else "scene_buffet", 512, 1360, 1460, 945, 890)
    tw = wt("H01", "一百九十八") - 0.15
    k = (t - tw) / 0.3
    if k > 0:
        sc = 1 + 1.0 * (1 - ease_out(k, 4))
        c.save()
        c.translate(420, 330)
        c.scale(sc, sc)
        c.translate(-420, -330)
        text(c, "¥198", 140, 430, SERIF(270), RED, a=clamp(k * 3))
        c.restore()
    anim_text(c, "吃回本了吗？", 150, 560, SERIF(76, 800), INK, t, wt("H01", "吃到") - 0.2, spacing=6)


def shot_cinema(c, t):
    t0 = s("H02") - 0.12
    c.clear(skia.Color4f(*NAVY, 1).toColor())
    cam(c, t, t0, s("H03"), 0.05)
    sx, sy_, sw, sh = 980, 120, 820, 440
    flick = 0.14 + 0.05 * math.sin(t * 9) + 0.03 * math.sin(t * 23)
    rrect(c, sx, sy_, sw, sh, 12, P((0.86, 0.9, 0.98), flick))
    glow(c, sx + sw / 2, sy_ + sh, 700, (0.7, 0.8, 1.0), a=flick * 0.8)
    tc = wt("H02", "片尾字幕") - 0.3
    if t > tc:
        f = SANS(26, 500)
        off = (t - tc) * 60
        c.save()
        c.clipRect(skia.Rect.MakeXYWH(sx, sy_, sw, sh))
        for i, line in enumerate(["导演", "编剧", "主演", "摄影", "剪辑", "配乐", "出品", "鸣谢", "THE END"]):
            text(c, line, sx + sw / 2, sy_ + sh + 40 + i * 52 - off, f, CREAM, align="center", a=0.55)
        c.restore()
    else:
        text(c, "z  z  z", sx + sw / 2, sy_ + sh / 2 + 30, SERIF(90, 700), CREAM, align="center",
             a=0.25 + 0.15 * math.sin(t * 3))
    # 整图：她靠在影院座椅里打瞌睡（人和座椅一起生成）
    to = cinema_seat(c, 1390, 1000, 520)
    big_number(c, t, wt("H02", "坐到了") - 0.1, "2", MUSTARD, x=170, y=520)
    anim_text(c, "小时", 470, 520, SERIF(110), MUSTARD, t, wt("H02", "坐到了"), spacing=6)
    anim_text(c, "硬撑到片尾", 180, 650, SERIF(64, 800), CREAM, t, wt("H02", "片尾字幕") - 0.2, spacing=6)


def cinema_seat(c, x, y, h, alpha=1.0):
    """座椅 + 打瞌睡的她；(x, y) 是座椅底座正下方的地面点"""
    c.drawOval(skia.Rect.MakeXYWH(x - h * 0.35, y - 12, h * 0.75, 24), P((0, 0, 0), 0.25 * alpha))
    return sprites.draw_at(c, "scene_cinema", 352, 1296, x, y, h, alpha=alpha)


def shot_queue(c, t):
    t0 = s("H03") - 0.12
    c.clear(skia.Color4f(*MUSTARD, 1).toColor())
    cam(c, t, t0, s("H04"), 0.04)
    c.drawRect(skia.Rect.MakeXYWH(0, 880, W, 200), P((0.85, 0.62, 0.22)))
    sprites.draw(c, "prop_teashop", 1700, 885, 560)
    # 前面排队的路人：每个人都不一样
    for i in range(6):
        px = 1400 - i * 135
        bob = 0.006 * math.sin(t * 1.6 + i)
        sprites.draw(c, f"crowd_{i % 6}", px, 885, [420, 380, 360, 400, 375, 410][i], sy=1 + bob)
    info = her(c, "queue", 520, 885, 440, t)
    tm = wt("H03", "四十分钟")
    mins = 40 * ramp(t, t0 + 0.2, tm + 0.6, ease_out)
    rrect(c, 140, 120, 470, 200, 26, P(INK))
    clock_digits(c, 375, 260, mins, 120, MUSTARD)
    anim_text(c, "前面还有", 150, 420, SANS(46, 600), INK, t, wt("H03", "前面还有") - 0.1)
    anim_text(c, "20 人", 360, 425, SERIF(84), RED, t, wt("H03", "二十个人") - 0.15, style="slam")


def shot_seven(c, t):
    t0 = SEC["hook_soft"]
    c.clear(skia.Color4f(*DUSK, 1).toColor())
    cam(c, t, t0, SEC["hook_back"], 0.07, 960, 650)
    c.drawRect(skia.Rect.MakeXYWH(0, 860, W, 220), P((0.25, 0.23, 0.35)))
    # 整图：两人坐在同一张长椅两端，各自看向别处（人和长椅一起生成）
    c.drawOval(skia.Rect.MakeXYWH(560, 868, 800, 34), P((0.12, 0.1, 0.2), 0.45))
    to = sprites.draw_at(c, "scene_bench", 768, 870, 960, 885, 540)
    t7 = wt("H04", "都七年了") - 0.2
    k = ramp(t, t7, t7 + 1.2, ease_out)
    if k > 0:
        text(c, "7", 760, 390, SERIF(300), CREAM, a=k * 0.95)
        text(c, "年", 960, 390, SERIF(110), CREAM, a=k * 0.9)
    anim_text(c, "只剩互相消耗", W / 2, 170, SERIF(58, 700), CREAM, t, wt("H04", "只剩") - 0.1, align="center",
              style="rise", spacing=6, a=0.8, t_out=t7 - 0.2)


def item_land_times():
    """四样东西落进背包的时间：从“都花了”开始，按八分音符一件接一件"""
    t = round((wt("H05", "都花了") + 0.35) / (BEAT / 2)) * (BEAT / 2)
    return [t + i * BEAT / 2 for i in range(4)]


def shot_reason(c, t):
    t0 = SEC["hook_back"]
    c.clear(skia.Color4f(*CREAM, 1).toColor())
    cam(c, t, t0, SEC["name"], 0.04, 640, 640)
    c.drawRect(skia.Rect.MakeXYWH(0, 880, W, 200), P((0.91, 0.86, 0.77)))
    lands = item_land_times()
    hx = 520
    # 每落进一件，人往下一沉；最后一件落下后换成背着鼓包、被压弯的样子
    dip = sum(math.exp(-(t - tl) * 14) * (0.012 + 0.006 * i) for i, tl in enumerate(lands) if t >= tl)
    if t < lands[-1]:
        info = sprites.draw(c, "her_straps", hx, 885, 530, sy=1 - dip)
    else:
        info = sprites.draw(c, "her_heavy", hx, 885, 530 * HEAVY_K, sy=1 - dip + 0.01 * math.sin(t * 1.2))
    bag = info.get("bag_c", (hx - 90, 560))
    xs = [170, 390, 610, 830]
    for i, (_, name, h, lab) in enumerate(ITEMS):
        t_in = s("H05") + 0.1 + i * 0.18
        k_in = ramp(t, t_in, t_in + 0.35, back)
        if k_in <= 0 or t >= lands[i]:
            continue
        x, y = xs[i], 180 + 8 * math.sin(t * 2 + i)
        # 落下：越落越快，缩小着掉进背包口
        kf = ramp(t, lands[i] - 0.38, lands[i], lambda u: u * u)
        x, y = lerp(x, bag[0], kf), lerp(y, bag[1] - 60, kf)
        sc = k_in * lerp(1.2, 0.45, kf)
        sprites.draw(c, name, x, y + h * sc / 2, h * sc, rot=(i - 1.5) * 6 * (1 - kf))
        text(c, lab, xs[i], 318, SERIF(44, 900), RED, align="center",
             a=k_in * (1 - ramp(t, lands[i] - 0.38, lands[i] - 0.2)))
    tb_ = s("H05")
    k = ramp(t, tb_, tb_ + 0.35, back)
    if k > 0:
        c.save()
        c.translate(1400, 330 + 8 * math.sin(t * 1.5))
        c.scale(k, k)
        c.translate(-1400, -330)
        bubble(c, 1000, 150, 830, 340, 900, 470, color=PAPER)
        c.restore()
    anim_text(c, "都花了这么多了", 1060, 260, SERIF(64, 800), INK, t, wt("H05", "都花了"), spacing=4)
    anim_text(c, "现在走，不就亏了吗？", 1060, 380, SERIF(70, 900), RED, t, wt("H05", "现在走"), spacing=4)


def shot_name(c, t):
    t0 = SEC["name"]
    c.clear(skia.Color4f(*NAVY, 1).toColor())
    dx = hit_shake(t, t0, 8)
    c.translate(dx, 0)
    flash(c, t, wt("T01", "沉没成本") - 0.1, (1, 1, 1), 0.18)
    cam(c, t, t0, s("T02"), 0.04)
    # 四个标签掉进一个黑洞：拿不回来
    hole = (W / 2, 760)
    c.drawOval(skia.Rect.MakeXYWH(hole[0] - 330, hole[1] - 60, 660, 120), P((0.0, 0.0, 0.02)))
    drop_at = [wt("T01", "钱"), wt("T01", "时间"), wt("T01", "时间") + 0.35, wt("T01", "感情")]
    for i, (_, name, h, _lab) in enumerate(ITEMS):
        tf = drop_at[i] - 0.1
        x = hole[0] + (i - 1.5) * 200
        # 掉落之前先悬在空中轻轻浮动
        if t < tf:
            y = 430 + 8 * math.sin(t * 2 + i)
            sprites.draw(c, name, x, y + h / 2, h, rot=(i - 1.5) * 8)
            continue
        k = ramp(t, tf, tf + 0.7, lambda x: x * x)
        if k >= 1:
            continue
        y = lerp(430, hole[1] + 40, k)
        sprites.draw(c, name, x, y + h / 2, h, rot=(i - 1.5) * 8 + k * 50, alpha=1 - k * 0.3)
    c.drawRect(skia.Rect.MakeXYWH(0, hole[1], W, H - hole[1]), P(NAVY))
    anim_text(c, "已经付出 · 拿不回来", W / 2, 160, SANS(48, 600), CREAM, t, wt("T01", "已经付出"), align="center",
              spacing=6, style="rise", t_out=wt("T01", "沉没成本") - 0.4)
    for word, x in (("钱", W / 2 - 300), ("时间", W / 2), ("感情", W / 2 + 300)):
        # 词出现在物件上方，物件同时往下掉，两者不重叠
        anim_text(c, word, x, 300, SERIF(110), MUSTARD, t, wt("T01", word) - 0.1, align="center", style="slam",
                  t_out=wt("T01", "沉没成本") - 0.35)
    tn = wt("T01", "沉没成本") - 0.1
    anim_text(c, "沉没成本", W / 2, 520, SERIF(200), CREAM, t, tn, align="center", spacing=30, style="slam",
              stagger=0.07)
    anim_text(c, "SUNK  COST", W / 2, 610, font("latin", 40), MUSTARD, t, tn + 0.4, align="center", spacing=10,
              style="rise")


def shot_heard(c, t):
    t0 = s("T02") - 0.2
    c.clear(skia.Color4f(*CREAM, 1).toColor())
    cam(c, t, t0, SEC["focus"], 0.04)
    c.drawRect(skia.Rect.MakeXYWH(0, 560, W, 30), P((0.91, 0.86, 0.77)))
    xs = [260, 470, 680, 960, 1240, 1450, 1660]
    order = [0, 1, 2, None, 3, 4, 5]
    tk = wt("T02", "可真轮到自己")
    for i, (x, ci) in enumerate(zip(xs, order)):
        k = ramp(t, t0 + i * 0.08, t0 + i * 0.08 + 0.35, back)
        if k <= 0:
            continue
        if ci is None:
            if t > tk:
                glow(c, x, 380, 230, RED, a=0.3 * ramp(t, tk, tk + 0.4))
            her(c, "heavy", x, 565, 345 * k, t)
        else:
            dim = 0.55 if t > tk else 1.0
            sprites.draw(c, f"crowd_{ci}", x, 565, [360, 330, 320, 350, 335, 355][ci] * k, alpha=dim)
        if t > wt("T02", "听过") and ci is not None:
            text(c, "✓", x, 140, SANS(54, 900), TEAL, align="center",
                 a=ramp(t, wt("T02", "听过"), wt("T02", "听过") + 0.3))
    anim_text(c, "这个词，很多人都听过", W / 2, 720, SERIF(66, 800), INK, t, t0 + 0.2, align="center", spacing=4)
    anim_text(c, "轮到自己，还是舍不得", W / 2, 850, SERIF(82, 900), RED, t, tk, align="center", spacing=4)


def shot_focus(c, t):
    """反砸：蓄力（压暗、收拢）→ 静音里只剩一束光和一句“为什么” → 小节线上整屏翻亮释放"""
    t0 = SEC["focus"]
    t_go = SEC["focus_go"]
    t_cut = t_go - 2 * BEAT
    if t < t_cut:
        # 蓄力：四周越来越暗，最后半小节文字往中心收
        c.clear(skia.Color4f(*NAVY, 1).toColor())
        her(c, "heavy", 300, 900, 420, t)
        k = ramp(t, t0, t_cut, lambda u: u)
        pull = ramp(t, t_cut - 2 * BEAT, t_cut, lambda u: u ** 2)
        c.save()
        c.translate(W / 2, 420)
        c.scale(1 - 0.08 * pull, 1 - 0.08 * pull)
        c.translate(-W / 2, -420)
        anim_text(c, "今天不讲", W / 2, 200, SANS(44, 600), GREY, t, t0 + 0.1, align="center", spacing=8)
        anim_text(c, "它是什么？", W / 2, 330, SERIF(84, 800), GREY, t, t0 + 0.3, align="center", spacing=6)
        strike(c, W / 2 - 230, W / 2 + 230, 300, RED, t, wt("T03", "只讲") - 0.2, width=9)
        anim_text(c, "只讲一件事", W / 2, 560, SERIF(110), CREAM, t, wt("T03", "只讲") - 0.1, align="center", spacing=14,
                  style="rise")
        c.restore()
        # 暗角：半径越来越小
        r = lerp(1500, 620, k) * (1 - 0.15 * pull)
        sh = skia.GradientShader.MakeRadial(skia.Point(W / 2, 480), r, [skia.Color4f(0, 0, 0, 0).toColor(),
                                            skia.Color4f(0, 0, 0, 0.92).toColor()], [0.35, 1.0])
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
    elif t < t_go:
        # 收缩：全黑，只有一束光照着她，轻声问“为什么”
        c.clear(skia.Color4f(0.02, 0.02, 0.04, 1).toColor())
        cx, gy = W / 2, 860
        path = skia.Path()
        path.moveTo(cx - 40, 0)
        path.lineTo(cx + 40, 0)
        path.lineTo(cx + 230, gy)
        path.lineTo(cx - 230, gy)
        path.close()
        c.drawPath(path, P((0.9, 0.88, 0.8), 0.07))
        c.drawOval(skia.Rect.MakeXYWH(cx - 230, gy - 22, 460, 44), P((0.9, 0.88, 0.8), 0.12))
        her(c, "heavy", cx, gy, 330, t)
        anim_text(c, "为什么，", W / 2, 300, SERIF(64, 800), (0.75, 0.75, 0.8), t, s("T03Q"), align="center", spacing=10,
                  style="rise")
    else:
        # 释放：整屏翻亮，放射线转动，大字砸下来；人物站稳不动
        c.clear(skia.Color4f(*MUSTARD, 1).toColor())
        ang = (t - t_go) * 6
        cx, cy = W / 2, 520
        for i in range(16):
            a0 = math.radians(ang + i * 22.5)
            a1 = math.radians(ang + i * 22.5 + 11.25)
            path = skia.Path()
            path.moveTo(cx, cy)
            path.lineTo(cx + 2400 * math.cos(a0), cy + 2400 * math.sin(a0))
            path.lineTo(cx + 2400 * math.cos(a1), cy + 2400 * math.sin(a1))
            path.close()
            c.drawPath(path, P((1, 0.93, 0.7), 0.35))
        c.drawRect(skia.Rect.MakeXYWH(0, 900, W, 180), P((0.85, 0.62, 0.22)))
        her(c, "heavy", 300, 905, 420, t)
        c.save()
        c.translate(hit_shake(t, t_go, 14), 0)
        text(c, "为什么", W / 2, 230, SERIF(64, 800), INK, align="center", a=0.7)
        anim_text(c, "你应该", W / 2, 420, SERIF(110), INK, t, s("T03R") - 0.1, align="center", spacing=14, style="slam")
        anim_text(c, "放下它", W / 2, 700, SERIF(240), RED, t, wt("T03R", "放下它") - 0.08, align="center", spacing=30,
                  style="slam", stagger=0.06)
        c.restore()
        flash(c, t, t_go, (1, 1, 1), 0.6, 0.35)


def reason_header(c, t, t0, num, color, line1, line2, bg_text=CREAM):
    # 冲击时只有标题文字抖动
    c.save()
    c.translate(hit_shake(t, t0, 10), 0)
    big_number(c, t, t0, num, color, x=120, y=400)
    anim_text(c, line1, 400, 230, SERIF(62, 800), bg_text, t, t0 + 0.25, spacing=4)
    anim_text(c, line2, 400, 340, SERIF(92, 900), color, t, t0 + 0.45, spacing=6)
    c.restore()


def shot_r1(c, t):
    t0 = SEC["r1"]
    c.clear(skia.Color4f(*TEAL, 1).toColor())
    reason_header(c, t, t0, "1", MUSTARD, "已经付出的", "早就回不来了")
    flash(c, t, t0, MUSTARD, 0.25)
    c.drawRect(skia.Rect.MakeXYWH(0, 890, W, 190), P((0.1, 0.36, 0.34)))
    info = her(c, "heavy", 700, 895, 520, t)
    # 钱、时间、感情：说到哪个出现哪个；说到“拿不回来”时变灰、沉下去消失
    t_gone = wt("R11", "就已经拿不回来了")
    gone = ramp(t, t_gone - 0.1, t_gone + 0.7, ease_in_out)
    for i, (word, name, h, x) in enumerate((("钱", "item_0", 190, 1150), ("时间", "item_1", 130, 1420),
                                             ("感情", "item_photo", 170, 1690))):
        tw = wt("R11", word) - 0.1
        k = ramp(t, tw, tw + 0.35, back)
        if k <= 0 or gone >= 1:
            continue
        y = 620 + 160 * gone + 6 * math.sin(t * 2 + i)
        tint = lerp((1, 1, 1), (0.55, 0.6, 0.6), gone)
        sprites.draw(c, name, x, y, h * k, alpha=1 - gone, rot=(i - 1) * 5,
                     tint=tint if gone > 0 else None)
        text(c, word, x, 700 + 160 * gone, SERIF(52, 900), PAPER, align="center", a=k * (1 - gone))
    # 两个选择：留下（座位）与离开（关着的门），都只是选项，不开门
    t_opt = s("R12") - 0.3
    # 账单卡片出现时，两个选项淡出
    ko = ramp(t, t_opt, t_opt + 0.45, back) * (1 - ramp(t, s("R13") - 0.2, s("R13") + 0.2))
    if ko > 0:
        for i, (label, prop, x, ph) in enumerate((("留下", "prop_seat", 1200, 380), ("离开", "prop_exit", 1580, 470))):
            hl = window_k(t, wt("R12", label) - 0.1, wt("R12", label) + 0.9)
            c.save()
            c.translate(x, 895)
            c.scale(ko * (1 + 0.04 * hl), ko * (1 + 0.04 * hl))
            c.translate(-x, -895)
            rrect(c, x - 160, 330, 320, 560, 26, P(PAPER, 0.10 + 0.12 * hl))
            sprites.draw(c, prop, x, 885, ph)
            text(c, label, x, 300, SERIF(56, 900), PAPER, align="center")
            c.restore()
        for i, x in enumerate((1200, 1580)):
            tt = wt("R12", "它们都回不来") + i * 0.2
            k = ramp(t, tt, tt + 0.4, back)
            if k > 0:
                # 被划掉的三样东西：不管选哪边都拿不回来
                for j, (name, h) in enumerate((("item_0", 90), ("item_1", 62), ("item_photo", 80))):
                    sprites.draw(c, name, x - 60 + j * 60, 470 + h * k / 2, h * k, alpha=k, rot=(j - 1) * 8)
                c.drawLine(x - 90, 400, x + 90, 540, stroke(RED, 11, k))
        anim_text(c, "都回不来", 1390, 210, SERIF(64, 900), PAPER, t, wt("R12", "都回不来") - 0.1, align="center", spacing=6)
    t3 = s("R13") - 0.2
    if t > t3:
        k = ramp(t, t3, t3 + 0.45, ease_out)
        rrect(c, 1080 + (1 - k) * 900, 140, 760, 470, 30, P(PAPER))
        cx = 1120 + (1 - k) * 900
        text(c, "这次选择要算的账", cx + 40, 230, SERIF(48, 900), INK)
        rows = [("已经付出的", wt("R13", "不该影响"), True), ("接下来怎么过", wt("R13", "接下来怎么过"), False)]
        for i, (label, tr, crossed) in enumerate(rows):
            y = 360 + i * 150
            kr = ramp(t, tr - 0.2, tr + 0.2, back)
            if kr <= 0:
                continue
            rrect(c, cx + 30, y - 70, 680, 120, 18, P(TEAL if not crossed else GREY, 0.15 * kr))
            text(c, label, cx + 70, y + 12, SERIF(64, 800), INK if not crossed else GREY, a=kr)
            if crossed:
                strike(c, cx + 60, cx + 420, y - 12, RED, t, tr + 0.2, width=8)
            else:
                text(c, "✓", cx + 640, y + 10, SANS(64, 900), TEAL, align="center", a=kr)


def shot_r2(c, t):
    t0 = SEC["r2"]
    c.clear(skia.Color4f(*NAVY, 1).toColor())
    reason_header(c, t, t0, "2", RED, "舍不得，会让你", "亏第二次")
    flash(c, t, t0, RED, 0.25)
    y0 = 480
    t1 = wt("R22", "电影票的钱")
    k1 = ramp(t, t1 - 0.2, t1 + 0.3, back)
    if k1 > 0:
        rrect(c, 120, y0, 820, 150, 20, P(CREAM, 0.08 * k1))
        text(c, "第一次", 160, y0 + 58, SANS(34, 500), CREAM, a=0.7 * k1)
        text(c, "票钱 ¥45", 160, y0 + 118, SERIF(56, 900), CREAM, a=k1)
        text(c, "已经亏了", 900, y0 + 100, SANS(42, 700), CREAM, align="right", a=0.6 * k1)
        strike(c, 150, 420, y0 + 100, RED, t, wt("R22", "已经亏了"), width=8)
    y1 = 670
    t2 = wt("R22", "再坐两个小时")
    k2 = ramp(t, t2 - 0.2, t2 + 0.3, back)
    if k2 > 0:
        rrect(c, 120, y1, 820, 190, 20, P(RED, 0.2 * k2))
        text(c, "第二次", 160, y1 + 58, SANS(34, 500), CREAM, a=0.7 * k2)
        text(c, "你的 2 小时", 160, y1 + 118, SERIF(56, 900), CREAM, a=k2)
        text(c, "正在亏", 900, y1 + 100, SANS(42, 800), RED, align="right", a=k2)
        drain = ramp(t, t2, t2 + 4.5, lambda x: x)
        rrect(c, 160, y1 + 150, 740, 16, 8, P(CREAM, 0.15 * k2))
        rrect(c, 160, y1 + 150, 740 * (1 - 0.85 * drain), 16, 8, P(RED, k2))
    ta = wt("R23", "运气不好")
    tb_ = wt("R23", "自己选的")
    ka = ramp(t, ta - 0.15, ta + 0.25, back)
    kb = ramp(t, tb_ - 0.15, tb_ + 0.25, back)
    # 右侧影院：揭示两种亏法时淡出
    fade = 1 - ramp(t, ta - 0.6, ta - 0.1)
    if fade > 0:
        rrect(c, 1060, 150, 760, 400, 14, P((0.86, 0.9, 0.98), (0.16 + 0.04 * math.sin(t * 7)) * fade))
        cinema_seat(c, 1480, 1000, 470, alpha=fade)
    if ka > 0:
        tag(c, 1160, y0 + 75, "运气不好", size=int(44 * ka), color=(0.75, 0.77, 0.8))
    if kb > 0:
        tag(c, 1180, y1 + 95, "自己选的", size=int(58 * kb), color=RED, ink=PAPER)


def shot_r3(c, t):
    t0 = SEC["r3"]
    c.clear(skia.Color4f(*MUSTARD, 1).toColor())
    reason_header(c, t, t0, "3", RED, "越晚放手", "亏得越多", bg_text=INK)
    flash(c, t, t0, (1, 1, 1), 0.3)
    # 坐标系
    ox, oy, gw, gh = 980, 900, 800, 560
    ka = ramp(t, t0 + 0.8, t0 + 1.4, ease_out)
    if ka > 0:
        c.drawLine(ox, oy, ox + gw * ka, oy, stroke(INK, 6))
        c.drawLine(ox, oy, ox, oy - gh * ka, stroke(INK, 6))
        text(c, "坚持的时间 →", ox + gw, oy + 56, SANS(34, 700), INK, align="right", a=ka)
        text(c, "离开的代价", ox - 20, oy - gh - 20, SANS(34, 700), INK, a=ka)
    curve = lambda u: (ox + gw * u, oy - gh * (math.exp(2.6 * u) - 1) / (math.exp(2.6) - 1))
    kc = ramp(t, s("R32") - 0.3, s("R32") + 1.5, ease_out)
    # 她一直站在坐标轴左边的起点（就是“现在”），面朝越来越陡的曲线
    her(c, "heavy", ox - 45, oy + 2, 190, t)
    if kc > 0:
        path = skia.Path()
        for i in range(61):
            u = i / 60 * kc
            x, y = curve(u)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        c.drawPath(path, stroke(RED, 10))
    # 两组例子沿曲线往上爬
    for (la, lb, ta, ua, ub) in (("40分钟", "1小时", wt("R32", "排了四十分钟"), 0.18, 0.32),
                                  ("3年", "5年", wt("R32", "投了三年"), 0.5, 0.78)):
        k = ramp(t, ta, ta + 2.2, ease_in_out)
        fade_ex = 1 - ramp(t, s("R33B") - 0.6, s("R33B"))
        if t < ta or fade_ex <= 0:
            continue
        u = lerp(ua, ub, k)
        x, y = curve(u)
        c.drawCircle(x, y, 16, P(INK, fade_ex))
        lab = la if k < 0.6 else lb
        # 曲线上的刻度用纯文字，不用吊牌样式
        # 平缓段标在点的正上方，陡峭段标在曲线右下方，都不压线、不压人
        if u < 0.45:
            text(c, lab, x + 10, y - 34, SERIF(50, 900), INK, align="center", a=fade_ex)
        else:
            text(c, lab, x + 24, y + 54, SERIF(50, 900), INK, a=fade_ex)
    # 每多撑一天：一个点沿曲线继续往上爬，离开的代价越来越高
    td = wt("R33", "每多撑一天")
    if t > td:
        k = ramp(t, td, s("R33B"), ease_in_out)
        fade_d = 1 - ramp(t, s("R33B") - 0.3, s("R33B") + 0.3)
        x, y = curve(lerp(0.78, 0.97, k))
        c.drawCircle(x, y, 18, P(RED, fade_d))
        glow(c, x, y, 70, (1, 0.4, 0.3), a=0.5 * fade_d)
    # 最便宜的离开时间：曲线起点亮起
    tn = wt("R33B", "最便宜") - 0.1
    t_now = SEC["r3_now"]
    t_cut = t_now - 2 * BEAT
    if t > tn:
        x, y = curve(0.02)
        k = ramp(t, tn, tn + 0.35, back)
        c.drawCircle(x, y, 26 * k, P(INK))
        glow(c, x, y, 120 * k, (1, 1, 1), a=0.6)
        anim_text(c, "最便宜的离开时间", 400, 520, SERIF(64, 900), INK, t, tn, spacing=4)
    # 停顿：音乐切掉的同时画面压暗，一圈光往起点收拢
    if t > t_cut:
        dim = ramp(t, t_cut, t_cut + 0.25)
        c.drawRect(skia.Rect.MakeWH(W, H), P((0.05, 0.05, 0.08), 0.78 * dim))
        x, y = curve(0.02)
        r = lerp(700, 26, ramp(t, t_cut, t_now, lambda u: u ** 1.5))
        c.drawCircle(x, y, r, stroke(CREAM, 5, 0.8 * dim))
        c.drawCircle(x, y, 26, P(CREAM, dim))
        # 她不被压暗：“现在”就是她站的地方
        her(c, "heavy", ox - 45, oy + 2, 190, t)
    # 现在：小节线上全屏翻转，正中一个巨大的“现在”
    if t >= t_now:
        c.clear(skia.Color4f(*INK, 1).toColor())
        for i in range(3):
            kr = ramp(t, t_now + i * 0.12, t_now + i * 0.12 + 1.2, ease_out)
            if 0 < kr < 1:
                c.drawCircle(W / 2, 560, 120 + 1300 * kr, stroke(MUSTARD, 10 * (1 - kr) + 2, 0.6 * (1 - kr)))
        c.save()
        c.translate(hit_shake(t, t_now, 16), 0)
        z = 1 + 0.04 * ramp(t, t_now, SEC["break"], lambda u: u)
        c.translate(W / 2, 560)
        c.scale(z, z)
        c.translate(-W / 2, -560)
        text(c, "最便宜的离开时间", W / 2, 250, SERIF(56, 800), CREAM, align="center", spacing=6, a=0.75)
        anim_text(c, "现在", W / 2, 700, SERIF(380), MUSTARD, t, t_now, align="center", spacing=40, style="slam",
                  stagger=0.05)
        c.restore()
        flash(c, t, t_now, (1, 1, 1), 0.7, 0.35)

def shot_break(c, t):
    t0 = SEC["break"]
    c.clear(skia.Color4f(0.05, 0.06, 0.1, 1).toColor())
    cam(c, t, t0, SEC["drop"], 0.12, W / 2, 700)
    glow(c, W / 2, 680, 520, (0.55, 0.6, 0.75), a=0.35)
    c.drawOval(skia.Rect.MakeXYWH(W / 2 - 320, 805, 640, 60), P((0.12, 0.13, 0.2)))
    t3 = SEC["break2"]
    # 抱膝坐着 → 渐强时慢慢站起来（交叉淡化）
    t_up = SEC["drop"] - BAR
    up = ramp(t, t_up, t_up + 0.25, ease_in_out)
    warm = ramp(t, t3 - 0.1, t3 + 1.0, ease_out)
    info = None
    if up < 1:
        info = sprites.draw(c, "her_floor_heavy", W / 2, 835, FLOOR_H, alpha=1 - up, sy=1 + 0.01 * math.sin(t * 1.3))
    if up > 0:
        info = her(c, "heavy", W / 2, 835, 470, t, alpha=up)
    # “没有白费”时背包开始发暖光：里面装的东西换回了答案
    if info and "bag_c" in info and warm > 0:
        bx, by = info["bag_c"]
        glow(c, bx, by, 260 * warm, (1.0, 0.8, 0.5), a=0.8 * warm)
    anim_text(c, "不是算不清账", W / 2, 230, SERIF(84, 800), (0.75, 0.78, 0.85), t, wt("C01", "不是算不清") - 0.1, align="center",
              style="rise", spacing=8, t_out=s("C02") - 0.2)
    anim_text(c, "那些付出，白费了？", W / 2, 230, SERIF(84, 800), (0.75, 0.78, 0.85), t, wt("C02", "那些付出") - 0.1,
              align="center", style="rise", spacing=8, t_out=t3 - 0.3)
    anim_text(c, "没有白费", W / 2, 250, SERIF(120), (1.0, 0.85, 0.6), t, s("C03") + 0.2, align="center", style="rise",
              spacing=14, stagger=0.09)


def shot_drop(c, t):
    t0 = SEC["drop"]
    c.save()
    k_sun = ramp(t, t0, SEC["tool"], lambda x: x)
    vgrad(c, lerp((0.09, 0.08, 0.2), (0.2, 0.18, 0.38), k_sun), lerp((0.98, 0.62, 0.38), (1.0, 0.76, 0.5), k_sun),
          0, 840, mid=(lerp((0.6, 0.33, 0.42), (0.78, 0.5, 0.5), k_sun), 0.62))
    sun_y = lerp(880, 780, k_sun)
    glow(c, 1500, sun_y, 620, (1, 0.88, 0.62), a=0.9)
    c.drawCircle(1500, sun_y, 95, P((1, 0.94, 0.78)))
    c.drawRect(skia.Rect.MakeXYWH(0, 840, W, 240), P((0.17, 0.12, 0.2)))
    t_card = s("C05")
    t_go = SEC["drop2"]
    x0 = 700
    # 放下背包：t_go 前后半秒，背包从背上落到地上
    drop_k = ramp(t, t_go - 0.35, t_go + 0.25, ease_in_out)
    t_away = round(wt("C06", "就可以走了") / BEAT) * BEAT
    if t >= t_away:
        # 远景：背包留在前景，她在远处迎着太阳
        c.drawOval(skia.Rect.MakeXYWH(250, 1000, 380, 40), P((0, 0, 0), 0.3))
        sprites.draw(c, "backpack_full", 440, 1015, 330)
        her(c, "card", 1290, 846, 200, t)
        bag_pos = (440, 900)
    elif drop_k <= 0:
        info = her(c, "heavy", x0, 845, 480, t)
        bag_pos = info.get("bag_c", (x0 - 80, 600))
    else:
        bag_x = lerp(x0 - 70, x0 - 190, drop_k)
        sprites.draw(c, "backpack_full", bag_x, 848, 220, alpha=min(1, drop_k * 3))
        bag_pos = (bag_x, 760)
        her(c, "card", x0, 845, 480, t)
    bx, by = bag_pos
    t_want = wt("C04", "自己想要什么")
    t_not = wt("C04", "什么不适合你")
    for i, (tt, label) in enumerate(((t_want, "想要什么"), (t_not, "不适合什么"))):
        k = ramp(t, tt - 0.2, tt + 0.5, ease_out)
        merge = ramp(t, t_card + 1.2, wt("C05", "一个答案"), ease_in_out)
        if k <= 0 or merge >= 1:
            continue
        tx = lerp(bx, 1000 + i * 420, k)
        ty = lerp(by - 120, 360 + i * 40, k)
        tx, ty = lerp(tx, 1250 - 160, merge), lerp(ty, 330, merge)
        sc = 1 - merge
        c.save()
        c.translate(tx + 160, ty)
        c.scale(sc, sc)
        c.translate(-(tx + 160), -ty)
        glow(c, tx + 160, ty, 240, a=0.8)
        rrect(c, tx, ty - 65, 320, 130, 18, P((1, 0.97, 0.88)))
        text(c, label, tx + 160, ty + 22, SERIF(58, 900), (0.5, 0.25, 0.15), align="center")
        c.restore()
    t_ans = wt("C05", "一个答案") - 0.1
    if t > t_ans:
        k = ramp(t, t_ans, t_ans + 0.45, back)
        to_hand = ramp(t, t_go - 0.8, t_go - 0.05, ease_in_out)
        hx, hy = x0 + 140, 600
        cx_, cy_ = lerp(1250, hx, to_hand), lerp(330, hy, to_hand)
        sc = lerp(2.1, 0.5, to_hand) * k
        a_card = 1 - ramp(t, t_go - 0.1, t_go + 0.15)
        if a_card > 0:
            glow(c, cx_, cy_, 260 * sc, a=0.9 * a_card)
            c.save()
            c.translate(cx_, cy_)
            c.scale(sc, sc)
            c.rotate(-6)
            rrect(c, -110, -70, 220, 140, 14, P((1, 0.97, 0.9), a_card))
            text(c, "答案", 0, 22, SERIF(64), (0.55, 0.3, 0.2), align="center", a=a_card)
            c.restore()
    # 冲击时只有大字抖动
    c.save()
    c.translate(hit_shake(t, t0, 10) + hit_shake(t, SEC["drop2"], 12), 0)
    anim_text(c, "那七年，让你知道了", W / 2, 170, SERIF(70, 800), (1, 0.97, 0.92), t, s("C04"), align="center", spacing=6,
              style="rise", t_out=s("C05") - 0.3)
    anim_text(c, "换回了一个答案", W / 2, 170, SERIF(80, 900), (1, 0.97, 0.92), t, wt("C05", "换回了") - 0.1,
              align="center", spacing=8, style="rise", t_out=t_go - 0.25)
    anim_text(c, "答案拿到了，", W / 2, 150, SERIF(96), (1, 0.97, 0.92), t, t_go, align="center", spacing=10, style="slam")
    anim_text(c, "就可以走了。", W / 2, 268, SERIF(96), (1, 0.97, 0.92), t, wt("C06", "就可以走了") - 0.05,
              align="center", spacing=10, style="slam")
    c.restore()
    c.restore()
    flash(c, t, t0, (1, 0.95, 0.85), 0.45, 0.3)
    flash(c, t, t_go, (1, 0.95, 0.85), 0.35, 0.25)


# ================================================================ 合：一个问题
def shot_tool(c, t):
    t0 = SEC["tool"]
    c.clear(skia.Color4f(*CREAM, 1).toColor())
    cam(c, t, t0, SEC["end"], 0.03)
    rrect(c, 260, 120, 1400, 430, 36, P(PAPER))
    rrect(c, 260, 120, 1400, 430, 36, stroke(INK, 4, 0.15))
    t_q = wt("K01", "如果今天")
    anim_text(c, "下次再犹豫，", W / 2, 300, SERIF(76, 800), GREY, t, s("K01"), align="center", spacing=6,
              t_out=t_q - 0.35)
    anim_text(c, "问自己一句：", W / 2, 430, SERIF(90, 900), INK, t, wt("K01", "问自己"), align="center", spacing=8,
              t_out=t_q - 0.35)
    anim_text(c, "如果今天从零开始，", W / 2, 290, SERIF(84, 900), INK, t, wt("K01", "如果今天") - 0.1, align="center",
              spacing=6)
    anim_text(c, "我还会选它吗？", W / 2, 440, SERIF(100), RED, t, wt("K01", "我还会") - 0.1, align="center", spacing=8)
    ta, tb_ = wt("K02", "如果会"), wt("K02", "如果不会")
    for i, (tt, a_, b_, col) in enumerate(((ta, "会", "继续", TEAL), (tb_, "不会", "放下它", RED))):
        k = ramp(t, tt - 0.15, tt + 0.3, back)
        if k <= 0:
            continue
        x = 330 + i * 660
        c.save()
        c.translate(x + 300, 760)
        c.scale(k, k)
        c.translate(-(x + 300), -760)
        rrect(c, x, 660, 600, 200, 100, P(col))
        text(c, f"{a_}  →  {b_}", x + 300, 792, SERIF(76, 900), PAPER, align="center")
        c.restore()


def shot_end(c, t):
    t0 = SEC["end"]
    c.clear(skia.Color4f(*NAVY, 1).toColor())
    cam(c, t, t0, TOTAL, 0.05)
    c.drawRect(skia.Rect.MakeXYWH(0, 900, W, 180), P((0.05, 0.08, 0.14)))
    # 地上只剩那个装满沉没成本的背包
    glow(c, W / 2, 860, 260, (1, 0.85, 0.6), a=0.25)
    c.drawOval(skia.Rect.MakeXYWH(W / 2 - 140, 892, 280, 26), P((0, 0, 0), 0.35))
    sprites.draw(c, "backpack_full", W / 2, 905, 210, alpha=ramp(t, t0, t0 + 0.6))
    anim_text(c, "你现在，", W / 2, 290, SERIF(80, 800), CREAM, t, s("E01"), align="center", spacing=8)
    anim_text(c, "有没有一件明知该放下、", W / 2, 450, SERIF(92), CREAM, t, wt("E01", "有没有") - 0.1, align="center",
              spacing=8)
    anim_text(c, "却还在硬撑的事？", W / 2, 600, SERIF(110), MUSTARD, t, wt("E01", "却还在") - 0.1, align="center",
              spacing=10)


SHOTS = [
    (0.0, s("H02") - 0.12, shot_buffet, False),
    (s("H02") - 0.12, s("H03") - 0.12, shot_cinema, True),
    (s("H03") - 0.12, SEC["hook_soft"], shot_queue, False),
    (SEC["hook_soft"], SEC["hook_back"], shot_seven, True),
    (SEC["hook_back"], SEC["name"], shot_reason, False),
    (SEC["name"], s("T02") - 0.2, shot_name, True),
    (s("T02") - 0.2, SEC["focus"], shot_heard, False),
    (SEC["focus"], SEC["r1"], shot_focus, True),
    (SEC["r1"], SEC["r2"], shot_r1, True),
    (SEC["r2"], SEC["r3"], shot_r2, True),
    # 第三条理由在“现在”之前压暗，字幕要跟着换成浅色
    (SEC["r3"], SEC["break"], shot_r3, lambda t: t > SEC["r3_now"] - 2 * BEAT),
    (SEC["break"], SEC["drop"], shot_break, True),
    (SEC["drop"], SEC["tool"], shot_drop, True),
    (SEC["tool"], SEC["end"], shot_tool, False),
    (SEC["end"], TOTAL + 1, shot_end, True),
]

# 大字已经完整表达的句子不再出字幕
SKIP_SUBS = {"K01", "E01", "C06", "T03Q", "T03R", "R33N"}


def build_subs():
    import re
    subs = []
    for lid, (a, b) in T.items():
        if lid in SKIP_SUBS:
            continue
        parts = re.findall(r"[^，。：；？！、]+[，。：；？！、]?", TEXT[lid])
        chunks = []
        for p in parts:
            body = p.rstrip("，。：；！、")
            if chunks and len(chunks[-1][0]) + len(body) <= 16 and len(body) <= 7:
                chunks[-1][0] += " " + body
                chunks[-1][1] += len(p)
            else:
                chunks.append([body, len(p)])
        tot = sum(n for _, n in chunks)
        cur = a
        for body, n in chunks:
            d = (b - a) * n / tot
            subs.append((cur, cur + d, body))
            cur += d
    return subs


SUBS = build_subs()
_grain = None


def render_frame(t, frame=0):
    global _grain
    if _grain is None:
        _grain = Grain()
    surf = surface(W, H)
    c = surf.getCanvas()
    dark = True
    for a, b, fn, is_dark in SHOTS:
        if a <= t < b:
            c.save()
            fn(c, t)
            c.restore()
            dark = is_dark(t) if callable(is_dark) else is_dark
            break
    # 字幕
    for a, b, body in SUBS:
        if a <= t < b:
            al = clamp((t - a) / 0.06) * clamp((b - t) / 0.06)
            f = SANS(46, 600)
            wd = f.measureText(body)
            col, shc = (CREAM, (0, 0, 0)) if dark else (INK, (1, 1, 1))
            sh = P(shc, 0.5 * al)
            sh.setImageFilter(skia.ImageFilters.Blur(5, 5))
            c.drawString(body, W / 2 - wd / 2, H - 64, f, sh)
            c.drawString(body, W / 2 - wd / 2, H - 66, f, P(col, al))
    # 片尾淡出
    fade = ramp(t, TOTAL - 1.0, TOTAL)
    if fade > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), P((0, 0, 0), fade))
    rgb = to_array(surf)[..., :3]
    return _grain.apply(rgb, frame)
