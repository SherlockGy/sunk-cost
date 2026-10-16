# 渲染：preview 抽帧拼图；video 分段并行渲染后与混音合成
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

from timeline import FPS, H, NFRAMES, W

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
LOG = "[render 渲染]"


def preview(times, name="sheet"):
    from scenes import render_frame
    (OUT / "preview").mkdir(parents=True, exist_ok=True)
    thumbs = []
    for t in times:
        img = render_frame(t, int(t * FPS))
        Image.fromarray(img).save(OUT / "preview" / f"t_{t:07.2f}.png")
        thumbs.append(Image.fromarray(img).resize((480, 270)))
    cols = 4
    sheet = Image.new("RGB", (480 * cols, 270 * ((len(thumbs) + cols - 1) // cols)))
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % cols) * 480, (i // cols) * 270))
    sheet.save(OUT / "preview" / f"{name}.png")


def chunk(args):
    a, b, path = args
    from scenes import render_frame
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(a, b):
        p.stdin.write(np.ascontiguousarray(render_frame(f / FPS, f)).tobytes())
    p.stdin.close()
    p.wait()
    return path


def video(workers=4, parts=8):
    (OUT / "chunks").mkdir(parents=True, exist_ok=True)
    size = (NFRAMES + parts - 1) // parts
    jobs = [(i * size, min(NFRAMES, (i + 1) * size), OUT / "chunks" / f"v{i}.mp4") for i in range(parts)]
    t0 = time.time()
    with ProcessPoolExecutor(workers) as ex:
        paths = list(ex.map(chunk, jobs))
    lst = OUT / "chunks" / "list.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in paths), encoding="utf-8")
    master = OUT / "沉没成本_母版.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i",
                    str(OUT / "mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                    "-shortest", "-movflags", "+faststart", str(master)], check=True)
    print(f"{LOG} 完成 {master}，用时 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    if sys.argv[1] == "preview":
        preview([float(x) for x in sys.argv[2:]])
    else:
        video(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
