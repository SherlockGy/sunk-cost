# 用 codex CLI 生成角色、道具和整图场景（并发执行，已存在的文件跳过）
# 先生成主角基准图，其余姿势都以基准图为参考，保证同一个人；人和道具有接触的镜头整图生成
#   python gen_chars.py base           只生成基准图
#   python gen_chars.py all [并发]      生成全部（按参考图依赖分批）
#   python gen_chars.py 名字1,名字2     只生成指定的几张
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "assets" / "chars_raw"
LOG = "[gen_chars 角色生成]"

STYLE = ("Modern flat vector illustration in a minimalist editorial poster style: clean geometric shapes, no outlines, "
         "two-tone soft cel shading, subtle paper grain, limited palette. Natural, relaxed, believable human proportions "
         "and gesture (not stiff), like a high-end animated explainer film. Simple face: small dark eye, small nose, "
         "small mouth, rosy cheek.")

HER = ("a young woman about 22 years old, slim and youthful, fresh college-student look, dark brown hair tied in a "
       "high bouncy ponytail with a few loose strands and short side bangs, wearing a loose cream-white sweatshirt, "
       "light-blue straight-leg jeans and white sneakers, carrying a medium coral-red backpack (#E2513A) on her back "
       "with both shoulder straps")
HER_NOBAG = HER.replace(", carrying a medium coral-red backpack (#E2513A) on her back with both shoulder straps",
                        ", no backpack")


def bg(key="green"):
    hexv, name = ("#00FF00", "green") if key == "green" else ("#FF00FF", "magenta")
    return (" Exactly one character, centered, full body fully visible with generous empty margin, not cropped, "
            "no cast shadow, no ground line, no props unless described, no text. "
            f"Background: perfectly flat solid pure {name} ({hexv}) with nothing else on it.")


def first(desc, pose):
    return f"{STYLE} Character: {desc}. {pose}" + bg()


def ref(pose, desc=None, key="green"):
    d = f" Character: {desc}." if desc else ""
    return ("Use the attached image as the exact character reference. Draw the SAME young woman with the identical "
            "face, hairstyle, clothing, colors, proportions and flat illustration style, and the SAME size and "
            f"position on the canvas (feet at the same height).{d} New pose: {pose} {STYLE}" + bg(key))


SIDE = "Strict side profile view facing RIGHT."
JOBS = {
    # 主角基准图：其余主角图都以它为参考
    "her_stand": dict(prompt=first(HER, f"Full body, standing relaxed, {SIDE} Arms hanging naturally, slight smile.")),
    # 主角的其他姿势
    "her_queue": dict(ref="her_stand", prompt=ref(f"{SIDE} Standing in a long queue, impatient and bored: weight on one leg, one hand holding a phone at chest height looking at it, the other hand on her hip, small frown.")),
    "her_straps": dict(ref="her_stand", prompt=ref(f"{SIDE} Standing, gripping both backpack shoulder straps tightly with both hands in front of her chest, shoulders raised, worried hesitant expression, looking slightly down.")),
    "her_card": dict(ref="her_stand", prompt=ref(f"{SIDE} Standing upright and relaxed, holding a small blank cream paper card in her near hand in front of her chest and looking at it with a gentle relieved smile.", desc=HER_NOBAG)),
    # 场景道具（同一画风，不带文字）
    "prop_seat": dict(prompt=STYLE + " A single empty cinema seat with deep red velvet cushion and armrest, strict side profile view facing RIGHT, the seat cushion folded down for sitting. No person, no text." + bg()),
    "prop_teashop": dict(prompt=STYLE + " A small trendy bubble-tea shop storefront kiosk, front view, with a striped awning, a menu board with only simple shapes (no readable text), a counter window, a big cute cup icon on the sign, warm lighting. No people, no text, no letters." + bg("magenta")),
    "prop_exit": dict(prompt=STYLE + " A single closed modern door with a small glowing exit sign above it showing only a running-man pictogram (no letters), front view, slightly ajar is NOT allowed: the door is fully closed. No people, no text." + bg("magenta")),
    # 人和道具有接触的镜头：整图生成，避免拼接时坐不稳、扶不上
    "scene_buffet": dict(ref="her_stand", prompt=(
        "Use the attached image as the exact character reference: draw the SAME young woman (identical face, ponytail, "
        "clothes, coral-red backpack, colors and flat illustration style). " + STYLE +
        " Scene, front view: the front facade of an all-you-can-eat buffet restaurant (fabric awning, wide open glass "
        "door showing a warm bright interior with food counters, one potted plant, a solid wall pillar on the LEFT side "
        "of the door). She has just walked out of the door and stands on the pavement just left of the door, body in "
        "three-quarter view facing toward the lower left, shuffling slowly. She LEANS her right shoulder against the wall "
        "pillar and rests her right forearm and palm flat on the wall surface beside her, elbow bent, her weight sagging "
        "onto the wall for support (clearly resting and steadying herself, NOT pushing). Her left hand gently rubs her "
        "stomach, which is only slightly full (she must NOT look pregnant). Eyes clearly OPEN, cheeks puffed out, "
        "overstuffed but satisfied expression, one small sweat drop. Feet flat on the pavement. No other people, no "
        "text, no letters. The whole scene sits on a perfectly flat solid pure magenta (#FF00FF) background with nothing "
        "else on it, no ground drawn beyond the pavement strip directly under the facade.")),
    "scene_buffet_b": dict(ref="scene_buffet", prompt=(
        "Use the attached image as the exact reference: the SAME restaurant facade, the SAME young woman, same style, "
        "same colors, same framing. Change only her pose: she sags sideways against the wall pillar, her right FOREARM "
        "lies flat against the pillar at shoulder height with the elbow bent and her head tilted to rest near it, her "
        "body weight visibly leaning on the wall, knees slightly bent, as if too full to walk properly. Her left hand "
        "holds her stomach. Eyes clearly OPEN, cheeks puffed, one small sweat drop. Background stays perfectly flat "
        "solid pure magenta (#FF00FF).")),
    "scene_cinema": dict(ref="her_stand", prompt=(
        "Use the attached image as the exact character reference: draw the SAME young woman (identical face, ponytail, "
        "clothes, coral-red backpack, colors and flat illustration style). " + STYLE +
        " Strict side profile view facing RIGHT: she sits slumped in a single cinema seat (dark burgundy velvet seat with "
        "an armrest and a black metal base). Her bottom rests fully ON the seat cushion, her back leans against the "
        "backrest with the backpack squeezed between her back and the backrest, thighs lie on the cushion, knees bent at "
        "the cushion's front edge, lower legs go down and BOTH feet rest flat on the floor in front of the seat. Head "
        "drooping forward, dozing off, eyes closed, hands resting on her lap. The seat and her are one solid grounded "
        "unit: no gaps, no floating. Only the seat and her, nothing else, no text." + bg())),
    "scene_bench": dict(ref="her_stand", prompt=(
        "Use the attached image as the exact character reference for the young woman: draw the SAME young woman "
        "(identical face, ponytail, clothes, coral-red backpack, colors and flat illustration style). " + STYLE +
        " Front view of one long wooden park bench with dark iron legs, both people sitting ON it, far apart at the two "
        "ends with a big empty gap in the middle. LEFT end: the young woman, sitting with her bottom on the seat planks, "
        "turned in side profile facing LEFT (away from him), shoulders dropped, head lowered, sad, hands on her knees, "
        "both feet flat on the ground, backpack still on her back. RIGHT end: a young man about 26, clearly different from "
        "her: tall, broad shoulders, short black hair with an undercut, thin black-rimmed glasses, dark olive-grey bomber "
        "jacket, black trousers, dark brown boots; sitting in side profile facing RIGHT (away from her), arms crossed, "
        "looking away, cold and distant, both feet flat on the ground. Their bottoms sit firmly on the bench, no floating. "
        "Only the bench and the two people, no text." + bg())),
    # 沉没成本的四个物件：小票、电影票（items 拆分）、计时器、合照
    "items": dict(prompt=STYLE + " Four separate small everyday objects in a row, evenly spaced with clear empty gaps so "
                  "they do not touch: 1) a long curled white restaurant receipt with only grey lines (no readable text), "
                  "2) a torn cinema ticket stub in mustard yellow with a simple film-strip icon, 3) a bubble tea cup with "
                  "a straw and black pearls, 4) a small instant photo (polaroid) of a young couple smiling together, "
                  "slightly faded. Each object upright and front view, roughly similar size. No text, no letters, no "
                  "numbers. Background: perfectly flat solid pure green (#00FF00) with nothing else on it."),
    # 计时器：生成后水平翻转，让指针停在约 40 分钟
    "item_timer": dict(post="mirror", prompt=STYLE + " Exactly ONE small object: a classic round silver-and-mustard "
                       "stopwatch timer with a top button, upright, front view, the hand pointing to about two-thirds of "
                       "the dial, simple tick marks only (no numbers, no text). Background: perfectly flat solid pure "
                       "green (#00FF00) with nothing else on it."),
    "item_photo": dict(ref="scene_bench", prompt=(
        STYLE + " Use the attached image as the character reference for BOTH people: the young woman with the dark brown "
        "high ponytail and cream sweatshirt, and the young man with the black undercut, thin black-rimmed glasses and "
        "olive bomber jacket. Draw ONLY one small instant photo (polaroid) object, upright, front view, white frame with a "
        "thicker bottom margin, slightly faded colors. Inside the photo: the SAME two people from the reference, years "
        "younger and happy, heads close together smiling, outdoor park background. No text. Background: perfectly flat "
        "solid pure green (#00FF00) with nothing else on it.")),
    # 四个物件拼成的参考图（本地合成，不调用 codex），供下面的鼓包图使用
    "items_ref2": dict(compose=["item_0", "item_1", "item_timer", "item_photo"], ref=["items", "item_timer", "item_photo"]),
    # 背着装满四个物件的鼓包：第二张参考图是四个物件
    "her_heavy": dict(ref=["her_straps", "items_ref2"], prompt=(
        "The FIRST attached image is the exact character reference: draw the SAME young woman (identical face, ponytail, "
        "clothes, colors, flat illustration style) at the SAME size and position on the canvas (feet at the same height). "
        "The SECOND attached image shows four objects. " + STYLE + " Strict side profile view facing RIGHT. Her SAME "
        "coral-red backpack is now overstuffed and bulging, much bigger and rounder, the top zipper half open, and the "
        "four objects from the second image clearly stick out of the opening: the long white receipt, the mustard cinema ticket, the round stopwatch and the polaroid photo. The heavy "
        "bag weighs her down: she leans forward, shoulders hunched, both hands gripping the shoulder straps in front of "
        "her chest, knees slightly bent, tired strained expression, eyes open looking down." + bg())),
    "her_floor_heavy": dict(ref=["her_heavy", "items_ref2"], prompt=(
        "The FIRST attached image is the exact character reference: the SAME young woman with the SAME overstuffed "
        "backpack, same flat illustration style. The SECOND attached image shows the four objects in the bag. " + STYLE +
        " Strict side profile view facing RIGHT. New pose: sitting on the floor hugging her knees: bottom on the ground, "
        "knees pulled up to her chest, both arms wrapped around her shins, head resting on her knees, sad. The bulging "
        "backpack is still on her back with the long white receipt, the mustard cinema ticket, the round stopwatch and the polaroid photo sticking out." + bg())),
    "backpack_full": dict(ref=["her_heavy", "items_ref2"], prompt=(
        "The FIRST attached image shows the exact design of the overstuffed coral-red backpack. The SECOND attached image "
        "shows the four objects in it. " + STYLE + " Draw ONLY that same backpack, no person, set down on the floor, seen "
        "from the side, straps relaxed on the floor, overstuffed and bulging, top zipper half open, with the long white receipt, the mustard cinema ticket, the round stopwatch and the polaroid photo"
        " sticking out." + bg())),
    # 排队的路人：六个外形各不相同的人
    "crowd": dict(prompt=STYLE + " A lineup of SIX different ordinary people standing in a row, evenly spaced with clear empty gaps "
                  "between them so they do not touch or overlap, all in strict side profile view facing RIGHT, full body, "
                  "varied ages, heights, builds, hairstyles and outfits: a tall man in a long coat, a short chubby man in a hoodie "
                  "with a cap, an elderly woman with grey bun and cardigan, a teenage boy with headphones, a woman with curly hair "
                  "and a tote bag, a man in a suit holding a coffee. Each in a slightly different relaxed standing pose. "
                  "No text. Background: perfectly flat solid pure green (#00FF00) with nothing else on it."),
}


def refs_of(spec):
    r = spec.get("ref") or []
    return [r] if isinstance(r, str) else list(r)


def compose_ref(name, spec):
    """把已抠好的物件横排拼在纯绿底上，作为参考图"""
    from prep_chars import CUT, main as prep
    prep(["items", "item_timer", "item_photo"])
    im = Image.new("RGB", (1800, 800), (0, 255, 0))
    x = 40
    for n in spec["compose"]:
        a = Image.open(CUT / f"{n}.png")
        h = 400 if n in ("item_1", "item_timer") else 560
        a = a.resize((int(a.width * h / a.height), h))
        im.paste(a, (x, (800 - h) // 2), a)
        x += a.width + 60
    im.save(RAW / f"{name}.png")
    return name, "ok 合成"


def run_job(name, spec):
    out = RAW / f"{name}.png"
    if out.exists():
        return name, "skip"
    if spec.get("compose"):
        return compose_ref(name, spec)
    prompt = ("Use your image generation tool to create exactly ONE image from the image prompt below, "
              f"then copy the resulting PNG file into the current working directory as {name}.png. "
              "Do not do anything else and do not create any other files.\n\nImage prompt:\n" + spec["prompt"])
    cmd = ["codex.cmd", "exec", "--skip-git-repo-check", "-s", "workspace-write"]
    for r_ in refs_of(spec):
        cmd += ["-i", str(RAW / f"{r_}.png")]
    cmd += ["-"]
    t = time.time()
    r = None
    for _ in range(2):
        r = subprocess.run(cmd, cwd=RAW, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if out.exists():
            if spec.get("post") == "mirror":
                ImageOps.mirror(Image.open(out)).save(out)
            return name, f"ok {time.time() - t:.0f}s"
    return name, "FAIL: " + (r.stdout or "")[-300:] + (r.stderr or "")[-300:]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    if mode == "base":
        names = ["her_stand"]
    elif mode == "all":
        names = list(JOBS)
    else:
        names = mode.split(",")
    # 按参考图依赖分批：一批里的任务所依赖的图都已经存在
    todo = list(names)
    while todo:
        ready = [n for n in todo if all((RAW / f"{r_}.png").exists() for r_ in refs_of(JOBS[n]))]
        if not ready:
            print(f"{LOG} 缺少参考图，无法继续：{todo}", flush=True)
            return
        with ThreadPoolExecutor(workers) as ex:
            for name, st in ex.map(lambda n: run_job(n, JOBS[n]), ready):
                print(f"{LOG}[{name}] {st}", flush=True)
        todo = [n for n in todo if n not in ready]


if __name__ == "__main__":
    main()
