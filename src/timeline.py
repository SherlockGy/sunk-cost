# 时间线：音乐 112 BPM（参考同类知识视频 BGM），每段开头的句子对齐到小节线，
# 让画面切换、重音冲击和旁白落在同一个强拍上
import json
import math
from pathlib import Path

from script import LINES

ROOT = Path(__file__).resolve().parent.parent
META = json.loads((ROOT / "assets" / "voice" / "durations.json").read_text(encoding="utf-8"))

FPS = 30
W, H = 1920, 1080
BPM = 112
BEAT = 60 / BPM
BAR = BEAT * 4
VOICE_LAG = 0.12        # 强拍之后旁白再进来一点点，冲击声不和字头打架

# 需要从小节线开始的段落（段落第一句）
SNAP = {"hook", "hook_soft", "hook_back", "name", "focus", "focus_go", "r1", "r3_now", "r2", "r3", "break", "break2", "drop", "drop2",
        "tool", "end"}
# 段落之前额外空出的小节数（给音乐的冲击、留白、渐强）
EXTRA_BARS = {"drop": 1, "r1": 1}
# 收尾贴着下一条小节线的段落：句子在小节线前这么多秒说完
#   数字：固定停顿（反砸里静音中的那句）
#   (最短, 最长)：紧接上一句说，停顿落在这个范围内，不够长就顺延到下一条小节线
PRE = {"focus_q": 0.3, "r3_pre": (0.45, 1.2)}

T = {}          # id -> (开始, 结束)
TEXT = {}
SECTION = {}    # 段落 -> 开始的小节线时间
_t = 0.0
_prev_sec = None
for lid, text, sec, gap in LINES:
    d = META[lid]["dur"]
    start = _t
    if sec != _prev_sec and sec in SNAP:
        bar_i = math.ceil((start - VOICE_LAG - 0.05) / BAR - 1e-9) + EXTRA_BARS.get(sec, 0.0)
        bar_t = max(0.0, bar_i * BAR)
        SECTION[sec] = bar_t
        start = bar_t + VOICE_LAG
    if sec in PRE and sec != _prev_sec:
        pre = PRE[sec]
        if isinstance(pre, tuple):
            # 紧接上一句；句尾到下一条小节线的停顿超过上限时，整句往后挪
            bar_t = math.ceil((start + d + pre[0]) / BAR - 1e-9) * BAR
            start = max(start, bar_t - pre[1] - d)
        else:
            # 找到能放下这句的下一条小节线，让句尾落在它前面 pre 秒
            bar_t = math.ceil((start + d + pre) / BAR - 1e-9) * BAR
            start = bar_t - pre - d
        SECTION[sec] = start
    T[lid] = (start, start + d)
    TEXT[lid] = text
    _t = start + d + gap
    _prev_sec = sec

TOTAL = round(_t + 0.3, 3)
NFRAMES = int(TOTAL * FPS)


def s(lid):
    return T[lid][0]


def e(lid):
    return T[lid][1]


def wt(lid, sub, frac=0.0):
    """词在句中开始的大致时间（按字数比例估算，标点按 1.6 个字计）"""
    a, b = T[lid]
    text = TEXT[lid]
    i = text.index(sub)
    wgt = [1.6 if ch in "，。：；？！、" else 1.0 for ch in text]
    tot = sum(wgt)
    pos = sum(wgt[:i]) + frac * sum(wgt[i:i + len(sub)])
    return a + (b - a) * pos / tot


def bar_of(t):
    return t / BAR


if __name__ == "__main__":
    for lid, (a, b) in T.items():
        print(f"{lid} {a:7.2f}-{b:7.2f} 小节 {a / BAR:6.2f}  {TEXT[lid]}")
    print("段落", {k: round(v, 2) for k, v in SECTION.items()})
    print("TOTAL", TOTAL, "小节", round(TOTAL / BAR, 1))
