# 沉没成本：为什么，你应该放下它

![封面](out/cover_16x9.png)

一支 2 分 31 秒的心理学短片。它不解释“沉没成本是什么”，只讲一件事：为什么你应该放下它。

- 成片：`out/沉没成本.mp4`（1920×1080，30 fps，H.264 + AAC，响度 -14 LUFS）
- 封面：`out/cover_16x9.png`（横版）、`out/cover_9x16.png`（竖版），各附一份 `.jpg`
- 画面、配乐、混音全部由本仓库的 Python 脚本生成；旁白由 MiniMax 语音合成，角色与道具图由 codex CLI 的图像生成功能绘制

> **成片下载**：前往本仓库的 [Releases](../../releases) 页面，下载 `sunk-cost.mp4`（约 288 MB）。横版、竖版封面的 PNG 和 JPG 文件也包含在附件中。仓库保留源码、素材和封面预览，视频通过 Release 提供。

## 片子的结构

| 时间 | 段落 | 内容 |
|---|---|---|
| 0:00 | 起 | 自助餐扶墙、电影硬撑到片尾、奶茶排队四十分钟、一段只剩互相消耗的七年感情 |
| 0:19 | 同一个理由 | “都花了这么多了”：小票、电影票、计时器、合照一件件掉进背包，她被压弯 |
| 0:26 | 点名 | 四样东西掉进坑里：这就叫沉没成本 |
| 0:39 | 反砸 | 蓄力 → 静音里轻声问“为什么，” → 小节线上全开：“你应该放下它” |
| 0:49 | 理由一 | 已经付出的，在选择之前就回不来了；这次选择只该算“接下来怎么过” |
| 1:06 | 理由二 | 舍不得会让你亏第二次：第一次是运气不好，第二次是自己选的 |
| 1:21 | 理由三 | 越晚放手亏得越多；停顿之后，“现在”单独落在小节线上 |
| 1:41 | 低谷 | 最难的不是算不清账，而是不想承认那些付出白费了 |
| 1:49 | 翻转与高潮 | 它们没有白费，换回了一个答案；她放下背包，下一个镜头已站在远处的太阳边 |
| 2:09 | 工具 | 下次再犹豫，问自己：如果今天从零开始，我还会选它吗？ |
| 2:21 | 结尾 | 地上只剩那个背包：你现在，有没有一件明知该放下、却还在硬撑的事？ |

## 设计要点

- 文案
  - 每句话的意思由字面直接说清楚，不依赖重读或轻读（语音合成读不出重音），强调交给画面大字。
  - “成本”一律是付出去的东西（钱、时间、感情），不用想得到的目标来代表成本。
- 节奏
  - 配乐 112 BPM、f 小调，结构是“律动 → 抽空 → 渐强 → 全开”；每段第一句对齐小节线。
  - 两个重心句做成“蓄力 → 静音停顿 → 释放”：“为什么，｜你应该放下它”和“永远是，｜现在”。台词拆成两句分别合成，停顿处音乐整段静音。
- 画面
  - 平面海报风格：色块 + 大字 + 简洁人物 + 信息图，画面保持锐利。
  - 人和道具有接触的镜头（靠墙、坐影院座椅、两人同坐长椅）整图生成，不做拼接。
  - 冲击时只有文字抖动，人物不跟着抖；人物不做走路动画，“离开”用剪辑省略表现。
- 声音
  - 不使用钟、铃、镲、三角铁等金属音色；音色来自 GeneralUser GS 音色库，再加合成的底鼓、低音和冲击音。
  - 旁白时音乐自动压低，整体响度归一到 -14 LUFS。

## 目录

```
sunk-cost/
├── src/
│   ├── script.py       旁白文案（每句的段落、句后停顿）
│   ├── narration.py    调 MiniMax 合成旁白；文案没变的句子不重复合成
│   ├── minimax.py      MiniMax 接口封装
│   ├── timeline.py     时间线：段落对齐小节线、反砸停顿、词的时间估算
│   ├── music.py        程序化配乐与混音（读取时间线）
│   ├── scenes.py       全部分镜，每个镜头都是时间的纯函数
│   ├── gfx.py          配色、缓动、文字动画等绘图工具
│   ├── draw_util.py    字体与画布
│   ├── sprites.py      位图角色/道具的摆放（脚底锚点、按身高缩放）
│   ├── render.py       抽帧预览；分段并行渲染并与混音合成
│   ├── cover.py        横竖两版封面
│   ├── gen_chars.py    用 codex CLI 生成角色、道具、整图场景
│   └── prep_chars.py   绿幕/品红幕抠图，记录脚底锚点和背包位置
├── assets/
│   ├── chars_raw/      codex 生成的原图（19 张）
│   ├── chars/          抠好的精灵图（23 张）与 meta.json
│   ├── voice/          旁白（30 句）与 durations.json
│   └── sf/             GeneralUser GS 音色库及其许可证
└── out/                成片与封面
```

## 环境

- Windows（字体从 `C:/Windows/Fonts` 读取）
  - 需要 `NotoSerifSC-VF.ttf`、`NotoSansSC-VF.ttf`（思源宋体/黑体可变字体）和 `NotoSerif-Bold.ttf`
  - 路径在 `src/draw_util.py` 的 `FONT_FILES` 中，换系统时改这里
- Python 3.12+，用 [uv](https://docs.astral.sh/uv/) 管理依赖
- ffmpeg（在 PATH 中），用于合成视频
- 只有重新生成素材时才需要：
  - MiniMax 账号（重新合成旁白）
  - codex CLI（重新生成角色图）

## 运行

仓库已包含全部旁白和角色素材，直接渲染即可：

```bash
cd src
uv run --project .. python music.py           # 配乐与混音 → out/mix.wav
uv run --project .. python render.py video 4  # 4 个进程并行渲染 → out/沉没成本_母版.mp4
uv run --project .. python cover.py           # 封面 → out/cover_*.png / .jpg
```

- 抽帧检查：`uv run --project .. python render.py preview 21.5 46 99.5`，单帧在 `out/preview/t_*.png`，拼图在 `out/preview/sheet.png`
- 母版画质很高、体积较大（约 1.3 GB），发布前再压一次：

```bash
ffmpeg -i out/沉没成本_母版.mp4 -c:v libx264 -preset slow -crf 18 -maxrate 16M -bufsize 32M -pix_fmt yuv420p -c:a copy -movflags +faststart out/沉没成本.mp4
```

修改文案后的完整流程：

```bash
uv run --project .. python narration.py       # 只重新合成改过的句子
uv run --project .. python music.py           # 时间线会自动顺延，配乐跟着重排
uv run --project .. python render.py video 4
```

重新生成角色图（可选）：

```bash
python gen_chars.py base                      # 主角基准图
python gen_chars.py all 4                     # 其余全部，按参考图依赖自动分批
uv run --project .. python prep_chars.py      # 抠图，更新 assets/chars
```

> 仓库里的三张“背鼓包”图（`her_heavy`、`her_floor_heavy`、`backpack_full`）实际是分两步得到的：先生成包里露出四样东西的版本，再让 codex 只替换其中一件物品，其他保持不变。`gen_chars.py` 里写的是一步到位的配方，重新生成时画面会与仓库里的版本略有不同，位置和比例可能需要在 `scenes.py` 里微调（例如弯腰图的比例系数 `HEAVY_K`）。

## 配置项

| 配置 | 位置 | 说明 |
|---|---|---|
| `MINIMAX_API_KEY` | 环境变量，或仓库根目录的 `.env` 文件 | MiniMax 接口密钥，只在重新合成旁白时需要 |
| `MINIMAX_API_BASE` | 同上 | 接口地址，默认 `https://api.minimax.cn` |

`.env` 已在 `.gitignore` 中，不会被提交。

可以调整的创作参数：

| 参数 | 位置 | 作用 |
|---|---|---|
| `VOICE`、`SPEED`、`TONE` | `src/script.py` | 音色、语速、多音字读音 |
| `BPM` | `src/timeline.py` | 配乐速度，所有段落按小节对齐 |
| `EXTRA_BARS` | `src/timeline.py` | 某段开始前额外空出的小节数 |
| `PRE` | `src/timeline.py` | 反砸停顿：句尾到下一条小节线的停顿时长 |
| `MUTES` | `src/music.py` | 由 `compose()` 填充的静音窗口，对应两处反砸停顿 |
| `HEAVY_K` | `src/scenes.py` | 弯腰图相对站直图的比例，保证身材一致 |

## 第三方内容

见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
