# 配乐：112 BPM，f 小调，借鉴知识讲解类 BGM 的结构（律动 → 抽空 → 渐强 → 全开）
# 不用任何金属音色：没有踩镲、镲片、铃、三角铁；高频律动用沙锤、拍手、响指
import json
import math
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import tinysoundfont as tsf
from scipy.io import wavfile
from scipy.ndimage import maximum_filter1d
from scipy.signal import butter, fftconvolve, sosfilt

from timeline import BAR, BEAT, SECTION, T, TOTAL, e, s, wt

ROOT = Path(__file__).resolve().parent.parent
SF2 = ROOT / "assets" / "sf" / "GeneralUser-GS.sf2"
VOICE = ROOT / "assets" / "voice"
OUT = ROOT / "out"
SR = 44100
N = int((TOTAL + 2.0) * SR)
LOG = "[music 配乐]"
rng = np.random.default_rng(112)

PARTS = {
    "piano": dict(prog=0, vol=0.95, pan=0.0, rev=0.35, lp=7000),
    "pluck": dict(prog=45, vol=0.85, pan=-0.25, rev=0.25),        # 拨弦
    "strings": dict(prog=48, vol=0.58, pan=0.15, rev=0.45),
    "stab": dict(prog=48, vol=0.55, pan=0.0, rev=0.4),
    "choir": dict(prog=52, vol=0.30, pan=0.0, rev=0.6),
    "harp": dict(prog=46, vol=0.6, pan=0.3, rev=0.4),
    "drums": dict(prog=0, bank=128, drums=True, vol=1.0, pan=0.0, rev=0.12),
}
KICK, CLAP, SHAKER, MARACAS, LTOM, MTOM, HTOM, CONGA_H, CONGA_L, SNAP_ = 36, 39, 82, 70, 45, 47, 50, 63, 64, 37

NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def m(name):
    base = NOTE[name[0]]
    i = 1
    if i < len(name) and name[i] in "#b":
        base += 1 if name[i] == "#" else -1
        i += 1
    return base + (int(name[i:]) + 1) * 12


# f 小调：i – VI – III – VII
CHORDS = {
    "Fm": ["F", "Ab", "C"], "Db": ["Db", "F", "Ab"], "Ab": ["Ab", "C", "Eb"], "Eb": ["Eb", "G", "Bb"],
    "Bbm": ["Bb", "Db", "F"], "Cm": ["C", "Eb", "G"], "Dbmaj7": ["Db", "F", "Ab", "C"], "Ebsus": ["Eb", "Ab", "Bb"],
}
PROG = ["Fm", "Db", "Ab", "Eb"]
MELODY = [  # 每小节 8 个八分音符位置，"-" 为休止或延长
    ["C5", "-", "Ab4", "-", "Bb4", "C5", "-", "-"],
    ["Ab4", "-", "F4", "-", "Ab4", "Bb4", "-", "-"],
    ["C5", "-", "Eb5", "-", "C5", "Bb4", "Ab4", "-"],
    ["G4", "-", "-", "-", "Bb4", "-", "Ab4", "G4"],
]


def tb(bar, beat=0.0):
    """小节、拍 → 秒"""
    return bar * BAR + beat * BEAT


class Score:
    def __init__(self):
        self.ev = {k: [] for k in PARTS}

    def note(self, part, t, dur, key, vel=80, human=0.006):
        if t < 0 or t > TOTAL + 1.5:
            return
        key = m(key) if isinstance(key, str) else key
        t = max(0.0, t + (rng.normal(0, human) if human else 0))
        self.ev[part].append((t, 1, "on", key, int(max(1, min(127, vel)))))
        self.ev[part].append((t + dur, 0, "off", key, 0))

    def chord(self, part, t, dur, keys, vel=70, roll=0.0):
        for i, k in enumerate(keys):
            self.note(part, t + i * roll, dur, k, vel)

    def cc(self, part, t, ctrl, val):
        self.ev[part].append((max(0.0, t), 0, "cc", ctrl, int(val)))

    def swell(self, part, t0, t1, v0, v1, steps=24):
        for i in range(steps + 1):
            k = i / steps
            self.cc(part, t0 + (t1 - t0) * k, 11, v0 + (v1 - v0) * k)


def voicing(ch, octave):
    names = CHORDS[ch]
    out = []
    prev = None
    for n_ in names:
        k = m(n_ + str(octave))
        while prev is not None and k <= prev:
            k += 12
        out.append(k)
        prev = k
    return out


# ---------------------------------------------------------------- 合成部分
def lp(x, f, order=2):
    return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), x, axis=0)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "highpass", fs=SR, output="sos"), x, axis=0)


class Bus:
    def __init__(self):
        self.buf = np.zeros((N, 2), np.float32)

    def add(self, t, sig, gain=1.0, pan=0.0):
        if sig.ndim == 1:
            sig = np.stack([sig * math.sqrt((1 - pan) / 2) * 1.414, sig * math.sqrt((1 + pan) / 2) * 1.414], 1)
        a = int(t * SR)
        if a < 0:
            sig, a = sig[-a:], 0
        b = min(N, a + len(sig))
        if b > a:
            self.buf[a:b] += sig[: b - a] * gain


def sub_bass(freq, dur, vel=1.0):
    """808 式低音：正弦 + 少量二次谐波，起音带一点点击感"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 0.6 * np.exp(-t * 60))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.18 * np.sin(2 * ph)
    env = np.minimum(1, t / 0.004) * np.exp(-t * 1.2) * np.minimum(1, (dur - t) / 0.03).clip(0, 1)
    return np.tanh(x * env * 1.4) * vel


def kick808(vel=1.0):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 35)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(np.sin(ph) * np.exp(-t * 6) * 2.2) * vel


def impact(vel=1.0):
    """冲击：低频下滑 + 短促的身体感，不含高频噪声"""
    n = int(3.0 * SR)
    t = np.arange(n) / SR
    f = 32 + 60 * np.exp(-t * 4)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 1.4)
    g = np.random.default_rng(3)
    thump = lp(g.standard_normal(n), 140) * np.exp(-t * 9) * 1.2
    return np.tanh((body + thump) * 1.3) * vel


def snap_click(vel=1.0, seed=0):
    """响指：短促的带通瞬态，高频但不刺耳"""
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    g = np.random.default_rng(seed)
    x = sosfilt(butter(2, [1400, 3600], "bandpass", fs=SR, output="sos"), g.standard_normal(n))
    return x * np.exp(-t * 70) * 1.6 * vel


# ---------------------------------------------------------------- 作曲
# 需要整段静音的时间窗（反砸的停顿）：(开始, 结束)
MUTES = []


def compose():
    S = Score()
    syn = Bus()
    sec = SECTION
    bar = lambda name: round(sec[name] / BAR)

    def groove(b0, b1, level=1.0, clap=True, shaker=True, kick=True, toms=False, snaps=False, bright=0.0):
        """鼓组律动：底鼓 1、2拍后半、3；拍手 2、4；沙锤十六分"""
        for b in range(b0, b1):
            for k8 in range(8):
                t = tb(b, k8 * 0.5)
                if kick and k8 in (0, 3, 4):
                    S.note("drums", t, 0.2, KICK, int((100 if k8 == 0 else 78) * level))
                    if k8 in (0, 4):
                        syn.add(t, kick808(0.32 * level))
                if clap and k8 in (2, 6):
                    S.note("drums", t, 0.2, CLAP, int(92 * level))
                if snaps and k8 in (2, 6):
                    syn.add(t + 0.01, snap_click(0.25 * level, seed=b * 8 + k8), pan=0.35)
            if shaker:
                for k16 in range(16):
                    t = tb(b, k16 * 0.25)
                    S.note("drums", t, 0.1, SHAKER if k16 % 2 == 0 else MARACAS,
                           int(min(127, (62 if k16 % 4 == 2 else 42) * level * (1 + 0.45 * bright))))
                    if bright > 0 and k16 % 4 == 3:
                        S.note("drums", t, 0.1, CLAP, int(50 * bright))
            if toms and b % 4 == 3:
                for i, (bt, tm) in enumerate(((3.0, HTOM), (3.25, MTOM), (3.5, MTOM), (3.75, LTOM))):
                    S.note("drums", tb(b, bt), 0.2, tm, int(85 * level))

    def bass(b0, b1, prog=PROG, level=1.0):
        for b in range(b0, b1):
            root = CHORDS[prog[b % 4]][0]
            f0 = 440 * 2 ** ((m(root + "1") - 69) / 12)
            for beat, dur, v in ((0, BEAT * 1.4, 1.0), (1.5, BEAT * 0.9, 0.7), (3.0, BEAT * 0.9, 0.8)):
                syn.add(tb(b, beat), sub_bass(f0, dur, 0.27 * v * level))

    def piano_arp(b0, b1, prog=PROG, vel=48, octave=3):
        for b in range(b0, b1):
            vc = voicing(prog[b % 4], octave)
            pat = [vc[0], vc[2], vc[0] + 12, vc[1] + 12, vc[2] + 12, vc[1] + 12, vc[0] + 12, vc[2]]
            for k8, key in enumerate(pat):
                S.note("piano", tb(b, k8 * 0.5), BEAT * 0.9, key, vel - (6 if k8 % 2 else 0))

    def piano_chords(b0, b1, prog=PROG, vel=50, octave=3):
        for b in range(b0, b1):
            S.chord("piano", tb(b), BAR * 0.98, [m(CHORDS[prog[b % 4]][0] + "2")] + voicing(prog[b % 4], octave + 1), vel,
                    roll=0.02)

    def melody(b0, b1, vel=70, octave_shift=0, part="piano", dur_mul=1.0):
        for b in range(b0, b1):
            row = MELODY[(b - b0) % 4]
            for k8, nm in enumerate(row):
                if nm == "-":
                    continue
                # 延长到下一个音
                L = 1
                while k8 + L < 8 and row[k8 + L] == "-":
                    L += 1
                S.note(part, tb(b, k8 * 0.5), BEAT * 0.5 * L * 0.95 * dur_mul, m(nm) + 12 * octave_shift, vel)

    def pluck(b0, b1, prog=PROG, vel=62):
        for b in range(b0, b1):
            vc = voicing(prog[b % 4], 4)
            for k8 in range(8):
                if k8 in (0, 3, 6) or k8 in (2,) and b % 2:
                    S.note("pluck", tb(b, k8 * 0.5), BEAT * 0.4, vc[k8 % 3], vel - (8 if k8 else 0))

    def pad(b0, b1, prog=PROG, vel=55, octave=3, part="strings"):
        for b in range(b0, b1):
            S.chord(part, tb(b), BAR * 1.02, voicing(prog[b % 4], octave), vel)

    def hit(t, big=1.0):
        syn.add(t, impact(0.75 * big))
        S.chord("stab", t, 0.5, [m("F2"), m("C3"), m("F3"), m("Ab3")], int(100 * big))
        S.chord("piano", t, 2.0, [m("F1"), m("F2")], int(110 * big))

    def reverse_swell(t_end, ch="Eb", dur=BAR):
        # 反向钢琴：用正弦近似钢琴泛音做一个渐强的“吸气”，落在 t_end
        n = int(dur * SR)
        tt = np.arange(n) / SR
        x = np.zeros(n)
        for k in voicing(ch, 3) + voicing(ch, 4):
            f = 440 * 2 ** ((k - 69) / 12)
            x += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 2.5) * 0.25
        x = x[::-1] * np.linspace(0, 1, n) ** 1.5
        syn.add(t_end - dur, x, 0.5)

    b_hook, b_soft, b_back, b_name = bar("hook"), bar("hook_soft"), bar("hook_back"), bar("name")
    b_focus, b_r1, b_r2, b_r3 = bar("focus"), bar("r1"), bar("r2"), bar("r3")
    b_break, b_break2, b_drop, b_drop2 = bar("break"), bar("break2"), bar("drop"), bar("drop2")
    b_tool, b_end = bar("tool"), bar("end")
    b_last = int(math.ceil(TOTAL / BAR))

    # 起：轻快律动（拨弦 + 拍手 + 沙锤），每个场景揭晓时有一下强调
    groove(b_hook, b_soft, level=0.85, toms=False)
    pluck(b_hook, b_soft)
    bass(b_hook, b_soft, level=0.8)
    piano_chords(b_hook, b_soft, vel=40)
    hit(0.0, 0.7)
    for lid, word in (("H01", "一百九十八"), ("H02", "片尾字幕"), ("H03", "四十分钟")):
        t = wt(lid, word)
        t = round(t / (BEAT / 2)) * (BEAT / 2)
        S.chord("stab", t, 0.25, [m("F3"), m("Ab3"), m("C4")], 90)
    # 七年：抽空，只剩钢琴
    for b in range(b_soft, b_back):
        S.chord("piano", tb(b), BAR, voicing(["Db", "Ab", "Eb"][(b - b_soft) % 3], 3), 44, roll=0.06)
    S.note("piano", wt("H04", "都七年了"), 2.4, "C5", 52)
    # 回到律动（只有底鼓与沙锤）
    groove(b_back, b_name, level=0.7, clap=False)
    piano_arp(b_back, b_name, vel=40)
    bass(b_back, b_name, level=0.7)
    # 点名：冲击 + 中等律动
    hit(tb(b_name), 1.0)
    groove(b_name, b_focus, level=0.8)
    piano_arp(b_name, b_focus, vel=44)
    bass(b_name, b_focus)
    pad(b_name, b_focus, vel=45)
    S.swell("strings", tb(b_name), tb(b_focus), 50, 80)
    # 聚焦 · 反砸：蓄力（两小节半逐渐加厚）→ 在强拍上一刀切成静音（收缩，只剩“为什么”）→ 小节线上全开（释放）
    b_go = bar("focus_go")
    t_cut = tb(b_go) - 2 * BEAT
    groove(b_focus, b_focus + 1, level=0.6, clap=False)
    groove(b_focus + 1, b_go - 1, level=0.8)
    piano_chords(b_focus, b_go - 1, vel=46)
    bass(b_focus, b_go - 1, level=0.75)
    pad(b_focus + 1, b_go - 1, vel=52)
    # 最后半小节：底鼓四分 + 拍手十六分越来越密越来越响，和弦与贝斯都在切点前收住
    b_last_ = b_go - 1
    ch = PROG[b_last_ % 4]
    for k4 in range(2):
        S.note("drums", tb(b_last_, k4), 0.2, KICK, 105)
        syn.add(tb(b_last_, k4), kick808(0.34))
    for k16 in range(8):
        S.note("drums", tb(b_last_, k16 * 0.25), 0.1, CLAP, 70 + k16 * 7)
    for k8 in range(8, 16):
        S.note("drums", tb(b_last_ - 1, k8 * 0.25), 0.1, CLAP, 45 + (k8 - 8) * 4)
    S.chord("piano", tb(b_last_), 2 * BEAT * 0.95, [m(CHORDS[ch][0] + "2")] + voicing(ch, 4), 58, roll=0.02)
    S.chord("strings", tb(b_last_), 2 * BEAT * 0.95, voicing(ch, 3), 70)
    root = CHORDS[ch][0]
    syn.add(tb(b_last_), sub_bass(440 * 2 ** ((m(root + "1") - 69) / 12), BEAT * 1.8, 0.3))
    S.swell("strings", tb(b_focus), t_cut, 30, 118)
    reverse_swell(t_cut, "Eb", BAR)
    MUTES.append((t_cut, tb(b_go)))
    # 释放：冲击 + 两小节完整律动，接第一条理由
    hit(tb(b_go), 1.3)
    groove(b_go, b_r1, level=1.0, toms=True, snaps=True, bright=0.6)
    bass(b_go, b_r1)
    piano_arp(b_go, b_r1, vel=50, octave=4)
    melody(b_go, b_r1, vel=74, octave_shift=1)
    pad(b_go, b_r1, vel=60)
    pad(b_go, b_r1, vel=46, octave=4, part="choir")
    # 三条理由：完整律动，逐条加层
    b_now = bar("r3_now")
    for b0, b1, extra in ((b_r1, b_r2, 0), (b_r2, b_r3, 1), (b_r3, b_now, 2)):
        hit(tb(b0), 1.0)
        groove(b0, b1, level=0.95, toms=extra >= 2, snaps=extra >= 1)
        piano_arp(b0, b1, vel=46)
        bass(b0, b1)
        melody(b0 + 1, b1, vel=64)
        if extra >= 1:
            pad(b0, b1, vel=50)
        if extra >= 2:
            pad(b0, b1, vel=40, octave=4, part="choir")
            for b in range(b0, b1):
                vc = voicing(PROG[b % 4], 5)
                for k8 in (1, 3, 5, 7):
                    S.note("harp", tb(b, k8 * 0.5), 0.3, vc[k8 % 3], 40)
    # “现在”：音乐在“永远是”下面切成静音，停顿之后在小节线上重重落下，然后余音过渡到低谷
    t_cut_now = tb(b_now) - 2 * BEAT
    reverse_swell(t_cut_now, "Eb", BAR)
    MUTES.append((t_cut_now, tb(b_now)))
    hit(tb(b_now), 1.3)
    S.chord("stab", tb(b_now), 0.8, [m("Ab2"), m("Eb3"), m("Ab3"), m("C4")], 115)
    S.chord("choir", tb(b_now), BAR * 1.1, voicing("Ab", 4) + [m("C5")], 78)
    S.chord("strings", tb(b_now), BAR * 1.1, voicing("Ab", 3), 70)
    S.chord("piano", tb(b_now), BAR * 1.1, [m("Ab1"), m("Ab2")] + voicing("Ab", 4), 90)
    # 抽空：只剩钢琴与弦乐长音
    for b in range(b_break, b_break2):
        S.chord("piano", tb(b), BAR, [m(CHORDS[PROG[b % 4]][0] + "2")] + voicing(PROG[b % 4], 4), 40, roll=0.08)
    pad(b_break, b_break2, vel=38)
    S.swell("strings", tb(b_break), tb(b_break2), 70, 30)
    # 其实它们没有白费：一个干净的钢琴音，随后渐强
    S.note("piano", s("C03") - 0.05, 3.0, "Ab4", 56)
    S.note("piano", s("C03") - 0.05, 3.0, "C5", 50)
    for b in range(b_break2, b_drop):
        vc = voicing(["Db", "Eb"][(b - b_break2) % 2], 4)
        for k8 in range(8):
            S.note("piano", tb(b, k8 * 0.5), BEAT * 0.45, vc[k8 % 3] if k8 % 2 == 0 else vc[(k8 + 1) % 3] + 12,
                   40 + (b - b_break2) * 14 + k8 * 2)
    pad(b_break2, b_drop, prog=["Db", "Eb", "Db", "Eb"], vel=58)
    S.swell("strings", tb(b_break2), tb(b_drop), 30, 115)
    for i in range(16):
        S.note("drums", tb(b_drop - 1, i * 0.25), 0.1, CLAP, 50 + i * 3)
    reverse_swell(tb(b_drop), "Eb", BAR * 1.5)
    # 全开：更亮（旋律高八度 + 弦乐 + 合唱），进行改为 VI–VII–i–i 推向光明
    DROP = ["Db", "Eb", "Fm", "Ab"]
    hit(tb(b_drop), 1.25)
    groove(b_drop, b_tool, level=1.0, toms=True, snaps=True, bright=1.0)
    bass(b_drop, b_tool, prog=DROP)
    piano_arp(b_drop, b_tool, prog=DROP, vel=50, octave=4)
    melody(b_drop, b_tool, vel=80, octave_shift=1)
    melody(b_drop, b_tool, vel=60, part="strings", dur_mul=1.6)
    pad(b_drop, b_tool, prog=DROP, vel=62)
    pad(b_drop, b_tool, prog=DROP, vel=52, octave=4, part="choir")
    for b in range(b_drop, b_tool):
        vc = voicing(DROP[b % 4], 5)
        for k16 in range(16):
            if k16 % 2 == 1 or k16 % 4 == 0:
                S.note("harp", tb(b, k16 * 0.25), 0.25, vc[(k16 // 2) % 3] + (12 if k16 % 8 == 7 else 0), 46)
    # 答案拿到了：最高点
    hit(tb(b_drop2), 1.35)
    S.chord("choir", tb(b_drop2), BAR * 2, voicing("Ab", 4) + [m("C5")], 80)
    # 合：轻一点的律动，带着希望
    hit(tb(b_tool), 0.6)
    groove(b_tool, b_end, level=0.7, clap=True)
    piano_arp(b_tool, b_end, prog=["Db", "Ab", "Eb", "Fm"], vel=44, octave=4)
    bass(b_tool, b_end, prog=["Db", "Ab", "Eb", "Fm"], level=0.8)
    pad(b_tool, b_end, prog=["Db", "Ab", "Eb", "Fm"], vel=40)
    # 结尾提问：鼓全停，钢琴停在一个不解决的和弦上
    S.chord("piano", tb(b_end), BAR * 2, [m("Db2")] + voicing("Dbmaj7", 3), 46, roll=0.1)
    S.chord("piano", tb(b_end + 2), BAR * 2.5, [m("Eb2")] + voicing("Ebsus", 3) + [m("F4")], 42, roll=0.12)
    pad(b_end, b_end + 4, prog=["Dbmaj7", "Dbmaj7", "Ebsus", "Ebsus"], vel=40)
    S.swell("strings", tb(b_end), TOTAL + 1, 80, 0)
    S.note("piano", TOTAL - 2.2, 2.5, "C5", 34)
    return S, syn


# ---------------------------------------------------------------- 渲染与混音
def render_part(spec, events, sfbytes):
    syn = tsf.Synth(samplerate=SR)
    sfid = syn.sfload(sfbytes)
    syn.program_select(0, sfid, spec.get("bank", 0), spec["prog"], spec.get("drums", False))
    syn.control_change(0, 11, 100)
    out = np.zeros((N, 2), np.float32)
    pos = 0
    for t, _, kind, a, b in sorted(events, key=lambda x: (x[0], x[1])):
        smp = min(N, int(t * SR))
        if smp > pos:
            out[pos:smp] = np.frombuffer(syn.generate_simple(smp - pos), np.float32).reshape(-1, 2)
            pos = smp
        if kind == "on":
            syn.noteon(0, a, b)
        elif kind == "off":
            syn.noteoff(0, a)
        elif kind == "cc":
            syn.control_change(0, a, b)
    if pos < N:
        out[pos:] = np.frombuffer(syn.generate_simple(N - pos), np.float32).reshape(-1, 2)
    return out


def reverb_ir(seconds=2.2, seed=5):
    m_ = int(seconds * SR)
    g = np.random.default_rng(seed)
    x = np.arange(m_) / SR
    ir = np.stack([lp(g.standard_normal(m_), 5000, 1) * np.exp(-x * 6.9 / seconds) for _ in range(2)], 1)
    ir[: int(0.02 * SR)] = 0
    return ir / np.sqrt((ir ** 2).sum(0))


def limiter(x, ceiling=0.89, look=0.005, release=0.12):
    a = np.abs(x).max(axis=1)
    pk = maximum_filter1d(a, size=2 * int(look * SR) + 1)
    g = np.minimum(1.0, ceiling / np.maximum(pk, 1e-9))
    step = 32
    gs = g[::step].copy()
    coef = math.exp(-step / (release * SR))
    for i in range(1, len(gs)):
        gs[i] = min(gs[i], coef * gs[i - 1] + (1 - coef) * gs[i])
    g2 = np.minimum(np.interp(np.arange(len(g)), np.arange(len(gs)) * step, gs), g)
    return x * g2[:, None]


def voice_track():
    v = np.zeros(N, np.float32)
    for lid, (a, _b) in T.items():
        sr, x = wavfile.read(VOICE / f"{lid}.wav")
        x = x.astype(np.float32) / 32768.0
        i = int(a * SR)
        v[i:i + len(x)] += x[: max(0, min(len(x), N - i))]
    return hp(v, 80)


def duck_curve(v, depth=0.5):
    env = np.convolve(np.abs(v), np.ones(int(0.05 * SR)) / int(0.05 * SR), mode="same")
    env = np.clip(env / (np.percentile(env[env > 1e-4], 90) + 1e-9), 0, 1)
    step = 64
    ds = env[::step]
    y = np.zeros_like(ds)
    prev = 0.0
    aa, ar = math.exp(-step / (0.06 * SR)), math.exp(-step / (0.5 * SR))
    for i, val in enumerate(ds):
        coef = aa if val > prev else ar
        prev = coef * prev + (1 - coef) * val
        y[i] = prev
    return 1 - depth * np.interp(np.arange(len(env)), np.arange(len(y)) * step, y)


def rms_curve(x, hop=0.25):
    h = int(hop * SR)
    n = len(x) // h
    return np.sqrt((x[: n * h].reshape(n, h, -1) ** 2).mean(axis=(1, 2)))


def main():
    S, syn = compose()
    sfbytes = SF2.read_bytes()
    dry = np.zeros((N, 2), np.float32)
    send = np.zeros((N, 2), np.float32)
    for name, evs in S.ev.items():
        if not evs:
            continue
        spec = PARTS[name]
        y = render_part(spec, evs, sfbytes)
        if spec.get("lp"):
            y = lp(y, spec["lp"], 1).astype(np.float32)
        p = spec["pan"]
        y[:, 0] *= math.sqrt((1 - p) / 2) * 1.414
        y[:, 1] *= math.sqrt((1 + p) / 2) * 1.414
        y *= spec["vol"]
        dry += y
        send += y * spec["rev"]
        print(f"{LOG}[{name}] 事件 {len(evs)}", flush=True)
    ir = reverb_ir()
    wet = np.stack([fftconvolve(send[:, c], ir[:, c])[:N] for c in range(2)], 1).astype(np.float32)
    music = dry + wet * 0.8 + syn.buf
    music = hp(music, 30).astype(np.float32)
    # 反砸的停顿：整段静音，两头 15ms 淡入淡出
    tt0 = np.arange(N) / SR
    for a_, b_ in MUTES:
        g = np.clip(np.maximum((a_ - tt0) / 0.015, (tt0 - b_) / 0.015 + 1), 0, 1)
        music *= g[:, None].astype(np.float32)
    # 结尾淡出
    tt = np.arange(N) / SR
    music *= np.clip((TOTAL + 0.8 - tt) / 1.6, 0, 1)[:, None]
    v = voice_track()
    duck = duck_curve(v, 0.5)[:, None]
    mus = music * duck
    mix = mus * 1.0 + np.stack([v, v], 1) * 0.55
    meter = pyln.Meter(SR)
    loud = meter.integrated_loudness(mix)
    mix = limiter(pyln.normalize.loudness(mix, loud, -14.0))
    loud2 = meter.integrated_loudness(mix)
    mix = limiter(pyln.normalize.loudness(mix, loud2, -14.0))
    OUT.mkdir(parents=True, exist_ok=True)
    g = 10 ** ((-14 - loud) / 20)
    np.save(OUT / "stems_rms.npy", np.stack([rms_curve(np.stack([v, v], 1) * 0.55 * g), rms_curve(mus * g),
                                              rms_curve(mus * 0)]))
    wavfile.write(OUT / "mix.wav", SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    mo = music / (np.abs(music).max() + 1e-9) * 0.85
    wavfile.write(OUT / "music_only.wav", SR, (mo * 32767).astype(np.int16))
    print(f"{LOG} 响度 {loud:.1f} → -14 LUFS，峰值 {np.abs(mix).max():.3f}，输出 {OUT / 'mix.wav'}")


if __name__ == "__main__":
    main()
