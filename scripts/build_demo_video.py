#!/usr/bin/env python3
"""Build the 1080p HouseMind AI product demo from real UI captures.

The visuals are produced from the same screenshots used in the README and PDF;
the narration is synthesized locally with macOS `say`.  This is an edited product
walkthrough, not a fake "live" recording: every number and screen shown is real.

Usage:
    .venv/bin/python scripts/build_demo_video.py
    .venv/bin/python scripts/build_demo_video.py --preview 6
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SCENES = json.loads((ROOT / "docs/demo_scenes.json").read_text())
W, H = 1920, 1080
FPS = 24
GAP = 0.85
LEAD = 0.35

INK = (10, 26, 21)
INK_2 = (16, 35, 29)
PAPER = (247, 243, 234)
GOLD = (176, 138, 82)
GOLD_LIGHT = (217, 195, 160)
MUTED = (170, 170, 156)

FONT_SERIF_CN = "/System/Library/Fonts/Supplemental/Songti.ttc"
FONT_SANS_CN = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_SANS_EN = "/System/Library/Fonts/Avenir Next.ttc"
FONT_SERIF_EN = "/System/Library/Fonts/Supplemental/Georgia.ttf"


def font(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size, index=index)


def fit_font(path: str, text: str, max_width: int, start: int, index: int = 0, min_size: int = 18):
    size = start
    while size > min_size:
        f = font(path, size, index)
        if f.getlength(text) <= max_width:
            return f
        size -= 2
    return font(path, min_size, index)


def wrap_cn(draw: ImageDraw.ImageDraw, text: str, f, max_width: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for ch in text:
        candidate = line + ch
        if draw.textlength(candidate, font=f) > max_width and line:
            lines.append(line)
            line = ch
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def text(draw, xy, s, f, fill, anchor="la", spacing=4):
    draw.multiline_text(xy, s, font=f, fill=fill, anchor=anchor, spacing=spacing)


def background() -> Image.Image:
    """Quiet dark-green gradient with an editorial grid."""
    base = Image.new("RGB", (W, H), INK)
    px = base.load()
    for y in range(H):
        t = y / H
        r = int(10 + 8 * t)
        g = int(24 + 14 * t)
        b = int(19 + 9 * t)
        for x in range(W):
            px[x, y] = (r, g, b)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for x in range(0, W, 80):
        d.line([(x, 0), (x, H)], fill=(230, 215, 185, 9), width=1)
    for y in range(0, H, 80):
        d.line([(0, y), (W, y)], fill=(230, 215, 185, 9), width=1)
    d.ellipse([W - 560, -260, W + 120, 420], fill=(176, 138, 82, 18))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


GRID_BG = background()

# The drop shadow is identical for every frame; blurring a full-HD layer per
# frame would dominate render time.
_SHADOW_DUMMY = Image.new("RGBA", (1570, 1015), (0, 0, 0, 0))
SHADOW = None


def screenshot_window(image_path: Path, zoom: float, focus: tuple[float, float]) -> tuple[Image.Image, tuple[int, int, int, int]]:
    shot = Image.open(image_path).convert("RGB")
    sw, sh = shot.size
    cw, ch = sw / zoom, sh / zoom
    cx, cy = focus[0] * sw, focus[1] * sh
    x0 = max(0, min(sw - cw, cx - cw / 2))
    y0 = max(0, min(sh - ch, cy - ch / 2))
    crop = shot.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch)))
    content_w, content_h = 1570, 981

    win = Image.new("RGBA", (content_w, content_h + 34), (18, 29, 25, 255))
    d = ImageDraw.Draw(win)
    d.rectangle([0, 0, content_w, 34], fill=(22, 36, 31, 255))
    for i, color in enumerate([(196, 101, 86), (204, 163, 82), (103, 145, 111)]):
        d.ellipse([16 + i * 19, 12, 25 + i * 19, 21], fill=color + (255,))
    url = "127.0.0.1:8000"
    d.rounded_rectangle([100, 8, content_w - 20, 26], radius=9, fill=(37, 51, 45, 255))
    d.text((116, 11), url, font=font(FONT_SANS_EN, 10, 0), fill=(168, 176, 166))

    content = crop.resize((content_w, content_h), Image.Resampling.BICUBIC)
    mask = Image.new("L", content.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, content_w, content_h], radius=10, fill=255)
    win.paste(content, (0, 34), mask)
    return win, (int(x0), int(y0), int(cw), int(ch))


def make_shadow() -> Image.Image:
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(shadow)
    x, y = 175, 25
    d.rounded_rectangle([x + 10, y + 18, x + 1570 + 10, y + 1015 + 18], radius=16, fill=(0, 0, 0, 120))
    return shadow.filter(ImageFilter.GaussianBlur(22))


def scene_frame(scene: dict, t: float, duration: float, total_t: float, total_duration: float) -> Image.Image:
    canvas = GRID_BG.copy()
    draw = ImageDraw.Draw(canvas)

    # Brand and scene status
    draw.rectangle([70, 42, 82, 54], fill=GOLD)
    draw.text((96, 38), "HOUSEMIND AI", font=font(FONT_SANS_EN, 16, 1), fill=(230, 222, 207))
    draw.text((96, 58), "PROPERTY INTELLIGENCE / DECISION WORKBENCH", font=font(FONT_SANS_EN, 8), fill=(154, 158, 146))
    draw.text((W - 70, 42), f"TECHNICAL DEMO · 2026  /  {scene['kicker'].split(' / ')[0]}", font=font(FONT_SANS_EN, 10), fill=(160, 160, 145), anchor="ra")

    if scene["image"]:
        focus = (0.5, 0.5)
        if scene.get("highlight"):
            x1, y1, x2, y2 = scene["highlight"]
            focus = ((x1 + x2) / 2, (y1 + y2) / 2)
        ease = 0.5 - 0.5 * math.cos(math.pi * min(1, t / max(duration, 0.01)))
        zoom = 1.0 + 0.022 * ease
        win, (cx, cy, cw, ch) = screenshot_window(ROOT / "docs" / scene["image"], zoom, focus)
        global SHADOW
        if SHADOW is None:
            SHADOW = make_shadow()
        canvas = Image.alpha_composite(canvas.convert("RGBA"), SHADOW).convert("RGB")
        x, y = 175, 25
        canvas.paste(win, (x, y), win)

        # Moving highlight over the real UI region.
        if scene.get("highlight"):
            hx1, hy1, hx2, hy2 = scene["highlight"]
            scale = 1570 / cw
            bx1 = int(x + (hx1 * 1600 - cx) * scale)
            by1 = int(y + 34 + (hy1 * 1000 - cy) * scale)
            bx2 = int(x + (hx2 * 1600 - cx) * scale)
            by2 = int(y + 34 + (hy2 * 1000 - cy) * scale)
            pulse = 0.5 + 0.5 * math.sin(t * 2.4)
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            ld.rounded_rectangle(
                [bx1, by1, bx2, by2], radius=8,
                fill=(176, 138, 82, int(12 + 10 * pulse)),
                outline=(205, 174, 123, int(190 + 40 * pulse)), width=2,
            )
            # corner ticks
            for (px, py, dx, dy) in [(bx1, by1, 1, 1), (bx2, by1, -1, 1), (bx1, by2, 1, -1), (bx2, by2, -1, -1)]:
                ld.line([(px, py), (px + 14 * dx, py)], fill=(232, 207, 166, 230), width=3)
                ld.line([(px, py), (px, py + 14 * dy)], fill=(232, 207, 166, 230), width=3)
            canvas = Image.alpha_composite(canvas.convert("RGBA"), layer).convert("RGB")
            draw = ImageDraw.Draw(canvas)

    # Bottom editorial caption
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for i in range(150):
        alpha = int(235 * (i / 149) ** 0.7)
        bd.line([(0, 930 + i), (W, 930 + i)], fill=(9, 23, 18, alpha))
    bd.line([(70, 930), (W - 70, 930)], fill=(176, 138, 82, 190), width=1)
    canvas = Image.alpha_composite(canvas.convert("RGBA"), band).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    draw.text((70, 950), scene["kicker"], font=font(FONT_SANS_EN, 11, 1), fill=(201, 176, 137))
    title_font = fit_font(FONT_SERIF_CN, scene["title"], 1400, 40, 0, 26)
    draw.text((70, 970), scene["title"], font=title_font, fill=(247, 241, 229))
    draw.text((70, 1022), scene["subtitle"], font=font(FONT_SANS_CN, 17), fill=(191, 190, 176))
    draw.text((W - 70, 1022), "辅助参考 · 非正式评估", font=font(FONT_SANS_CN, 13), fill=(150, 155, 143), anchor="ra")

    # Progress
    draw.rectangle([0, H - 4, int(W * min(1, total_t / total_duration)), H], fill=GOLD)
    draw.rectangle([int(W * min(1, total_t / total_duration)), H - 4, W, H], fill=(32, 43, 37))

    # Dip to black at scene boundaries for clean cuts.
    fade = 0.0
    if t < 0.28:
        fade = 1 - t / 0.28
    elif duration - t < 0.28:
        fade = 1 - (duration - t) / 0.28
    if fade > 0:
        black = Image.new("RGBA", (W, H), (4, 10, 8, int(255 * fade * 0.9)))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), black).convert("RGB")
    return canvas


def title_frame(scene: dict, t: float, duration: float, outro: bool = False) -> Image.Image:
    canvas = GRID_BG.copy()
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    # subtle vertical gold rule
    d.rectangle([70, 120, 72, H - 120], fill=(176, 138, 82, 80))
    d.text((120, 130), scene["kicker"], font=font(FONT_SANS_EN, 11, 1), fill=(201, 176, 137))

    if not outro:
        main = "HouseMind AI"
        f = font(FONT_SERIF_EN, 84, 0)
        d.text((120, 230), "House", font=f, fill=(250, 245, 234))
        d.text((120 + f.getlength("House"), 230), "Mind AI", font=font(FONT_SERIF_EN, 84, 0), fill=GOLD_LIGHT)
        d.text((124, 350), "读懂市场，再决定。", font=font(FONT_SERIF_CN, 44), fill=(231, 219, 198))
        d.line([(124, 430), (820, 430)], fill=(176, 138, 82, 180), width=1)
        d.text((124, 456), "AI 房产估值与投资决策工作台", font=font(FONT_SANS_CN, 20), fill=(186, 184, 168))
        chips = ["XGBoost", "TreeSHAP", "80% INTERVAL", "RAG", "AGENT"]
        cx = 124
        for chip in chips:
            tw = d.textlength(chip, font=font(FONT_SANS_EN, 11))
            d.rounded_rectangle([cx, 530, cx + tw + 28, 562], radius=16, outline=(176, 138, 82, 160), width=1)
            d.text((cx + 14, 540), chip, font=font(FONT_SANS_EN, 11), fill=(213, 196, 169))
            cx += tw + 40
        d.text((124, H - 150), "TECHNICAL DEMO  ·  05:40  ·  1080P", font=font(FONT_SANS_EN, 11), fill=(139, 145, 132))
    else:
        d.text((120, 250), "读懂市场，", font=font(FONT_SERIF_CN, 70), fill=(247, 241, 229))
        d.text((120, 350), "再决定。", font=font(FONT_SERIF_CN, 70), fill=GOLD_LIGHT)
        d.line([(124, 465), (780, 465)], fill=(176, 138, 82, 180), width=1)
        d.text((124, 492), "数据 · 区间 · 解释 · 边界", font=font(FONT_SANS_CN, 22), fill=(193, 190, 174))
        stats = [("$59,477", "XGBoost MAE"), ("81.5%", "区间覆盖率"), ("$95,130", "未见邮编 MAE")]
        sx = 124
        for value, label in stats:
            d.text((sx, 590), value, font=font(FONT_SERIF_EN, 28, 0), fill=(237, 224, 202))
            d.text((sx, 630), label, font=font(FONT_SANS_CN, 13), fill=(160, 164, 151))
            sx += 280
        d.text((124, H - 150), "HOUSEMIND AI  /  2026  /  THANK YOU", font=font(FONT_SANS_EN, 11), fill=(139, 145, 132))

    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    # fade in/out
    fade = 1.0
    if t < 0.7:
        fade = t / 0.7
    if duration - t < 0.7:
        fade = min(fade, (duration - t) / 0.7)
    if fade < 1:
        black = Image.new("RGBA", (W, H), (4, 10, 8, int(255 * (1 - fade))))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), black).convert("RGB")
    return canvas


def build_audio(scenes: list[dict], out_wav: Path, work: Path) -> list[float]:
    durations: list[float] = []
    for i, scene in enumerate(scenes):
        txt = work / f"narr-{i}.txt"
        aiff = work / f"narr-{i}.aiff"
        wav = work / f"narr-{i}.wav"
        txt.write_text(scene["narration"])
        subprocess.run(["say", "-v", "Tingting", "-r", "170", "-o", str(aiff), "-f", str(txt)], check=True)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", str(aiff), str(wav)], check=True)
        info = subprocess.run(["afinfo", str(aiff)], capture_output=True, text=True).stdout
        durations.append(float(re.search(r"estimated duration: ([\d.]+)", info).group(1)))

    with wave.open(str(out_wav), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(44100)
        out.writeframes(b"\x00\x00" * int(LEAD * 44100))
        wavs = sorted(work.glob("narr-*.wav"), key=lambda path: int(path.stem.split("-")[1]))
        for wav in wavs:
            idx = int(wav.stem.split("-")[1])
            with wave.open(str(wav), "rb") as src:
                out.writeframes(src.readframes(src.getnframes()))
            if idx < len(scenes) - 1:
                out.writeframes(b"\x00\x00" * int(GAP * 44100))
        out.writeframes(b"\x00\x00" * int(0.8 * 44100))
    return durations


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=int, default=0, help="render every Nth frame only")
    parser.add_argument("--out", default="docs/HouseMind_AI_Demo_1080p.mp4")
    args = parser.parse_args()

    if not shutil.which("say") or not shutil.which("afconvert"):
        raise SystemExit("macOS say/afconvert not available")

    work = Path(tempfile.mkdtemp(prefix="housemind-video-"))
    print("→ synthesizing narration")
    durations = build_audio(SCENES, work / "narration.wav", work)
    scene_lengths = [d + (GAP if i < len(SCENES) - 1 else 0.8) for i, d in enumerate(durations)]
    total_duration = LEAD + sum(scene_lengths)
    print(f"→ audio {sum(durations):.1f}s, video {total_duration:.1f}s ({total_duration/60:.2f} min)")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-", "-i", str(work / "narration.wav"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-shortest", "-movflags", "+faststart",
        "-metadata", "title=HouseMind AI — 产品演示",
        str(ROOT / args.out),
    ]
    print("→ encoding", " ".join(cmd[:8]), "…")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    frame_no = 0
    t_global = 0.0
    for si, scene in enumerate(SCENES):
        dur = scene_lengths[si]
        frames = int(round(dur * FPS))
        for local in range(frames):
            if args.preview and local % args.preview:
                frame_no += 1
                continue
            t = local / FPS
            if scene["image"]:
                img = scene_frame(scene, t, dur, t_global + t, total_duration)
            else:
                img = title_frame(scene, t, dur, outro=scene["id"] == "outro")
            proc.stdin.write(img.tobytes())
            frame_no += 1
            if frame_no % 240 == 0:
                print(f"  {frame_no} frames / {t_global + t:.1f}s", flush=True)
        t_global += dur
    proc.stdin.close()
    proc.wait()
    if proc.returncode:
        raise SystemExit(f"ffmpeg failed: {proc.returncode}")
    print(f"✓ wrote {ROOT / args.out}")
    print(f"  work dir: {work}")


if __name__ == "__main__":
    main()
