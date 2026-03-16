#!/usr/bin/env python3

import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple
import re

from PIL import Image, ImageDraw, ImageFont


CANVAS = (1242, 1660)
MARGIN_X = 96
TOP_Y = 110

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "\U0000200D"
    "\U0000FE0F"
    "]+",
    flags=re.UNICODE,
)


def sanitize_text(text: str) -> str:
    if not text:
        return ""
    return EMOJI_PATTERN.sub("", text)



def load_package(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def pick_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/System/Library/Fonts/Supplemental/Songti.ttc",
                "/System/Library/Fonts/STHeiti Medium.ttc",
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/System/Library/Fonts/Supplemental/Songti.ttc",
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
            ]
        )

    for font_path in candidates:
        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    if not text:
        return []
    words = list(text)
    lines: List[str] = []
    current = ""
    for ch in words:
        test = current + ch
        width = draw.textbbox((0, 0), test, font=font)[2]
        if width <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def draw_paragraph(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: Tuple[int, int],
    font: ImageFont.ImageFont,
    max_width: int,
    fill: str,
    line_gap: int,
) -> int:
    x, y = xy
    lines = wrap_text(draw, text, font, max_width)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, y), line, font=font)
        y = bbox[3] + line_gap
    return y


def make_cover(package: Dict, out_path: Path) -> None:
    image = Image.new("RGB", CANVAS, "#FFF4E8")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((60, 80, 1182, 1580), radius=60, fill="#FFFFFF")

    title = sanitize_text(
        package.get("cover", {}).get("title") or package.get("title") or package.get("topic") or "小红书笔记"
    )
    subtitle = sanitize_text(package.get("cover", {}).get("subtitle") or "把复杂内容讲清楚")

    accent = "#FF5A3D"
    draw.rounded_rectangle((100, 120, 1142, 520), radius=48, fill=accent)
    title_font = pick_font(86, bold=True)
    y = 170
    for line in wrap_text(draw, title, title_font, 900):
        draw.text((130, y), line, font=title_font, fill="#FFFFFF")
        bbox = draw.textbbox((130, y), line, font=title_font)
        y = bbox[3] + 20

    subtitle_font = pick_font(40, bold=True)
    sub_w = draw.textbbox((0, 0), subtitle, font=subtitle_font)[2]
    sub_x = 130
    draw.rounded_rectangle((sub_x, y + 10, sub_x + sub_w + 48, y + 74), radius=28, fill="#1B1B1B")
    draw.text((sub_x + 24, y + 24), subtitle, font=subtitle_font, fill="#FFFFFF")

    body = package.get("body", "")
    highlights = []
    for para in [p.strip() for p in body.split("\n") if p.strip()]:
        highlights.append(sanitize_text(para))
        if len(highlights) == 3:
            break

    panel_top = 760
    draw.rounded_rectangle((110, panel_top, 1132, 1460), radius=48, fill="#FFF1E6")
    draw.text((150, panel_top + 40), "看点速读", font=pick_font(44, bold=True), fill="#A33A2B")
    bullet_font = pick_font(38)
    bullet_y = panel_top + 120
    max_y = 1400
    for item in highlights or ["核心观点更清晰", "争议与转折更明确", "结论更好记"]:
        next_y = draw_paragraph(draw, f"● {item}", (150, bullet_y), bullet_font, 880, "#2A2522", 16)
        if next_y > max_y:
            break
        bullet_y = next_y + 8

    image.save(out_path)


def make_page(page: Dict, index: int, total: int, out_path: Path) -> None:
    palette = [
        ("#FFF7F0", "#1E1C1A", "#FF5A3D", "#FFE3D4"),
        ("#F4F9FB", "#1E1F22", "#2E7D6B", "#DFF2EE"),
        ("#FFF6EE", "#1B1B1B", "#E58A3A", "#FFE6D3"),
    ]
    bg, fg, accent, panel = palette[(index - 1) % len(palette)]
    image = Image.new("RGB", CANVAS, bg)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((70, 80, 1172, 1580), radius=56, fill="#FFFFFF")
    draw.rounded_rectangle((90, 110, 310, 198), radius=28, fill=accent)
    draw.text((125, 134), f"第 {index} 页", font=pick_font(36, bold=True), fill="#FFFFFF")
    draw.text((1005, 132), f"{index}/{total}", font=pick_font(32), fill="#6C6C72")

    heading = sanitize_text(page.get("heading") or f"重点 {index}")
    draw.rounded_rectangle((90, 250, 1150, 430), radius=42, fill=panel)
    draw_paragraph(draw, heading, (130, 290), pick_font(58, bold=True), 920, fg, 18)

    draw.rounded_rectangle((90, 480, 1150, 1400), radius=44, fill="#F9F7F4")
    draw.rounded_rectangle((110, 520, 130, 1360), radius=10, fill=accent)
    bullet_font = pick_font(44)
    bullet_y = 560
    for bullet in page.get("bullets", [])[:6]:
        text = f"● {sanitize_text(str(bullet))}"
        bullet_y = draw_paragraph(draw, text, (170, bullet_y), bullet_font, 860, fg, 16)
        bullet_y += 12

    footer = sanitize_text(page.get("footer") or "")
    if footer:
        draw.rounded_rectangle((160, 1440, 1080, 1515), radius=30, fill=accent)
        footer_font = pick_font(32, bold=True)
        footer_width = draw.textbbox((0, 0), footer, font=footer_font)[2]
        footer_x = max(180, math.floor((CANVAS[0] - footer_width) / 2))
        draw.text((footer_x, 1462), footer, font=footer_font, fill="#FFFFFF")

    image.save(out_path)


def normalize_pages(package: Dict) -> List[Dict]:
    pages = package.get("image_pages") or package.get("pages") or []
    if pages:
        return pages

    body = package.get("body", "")
    blocks = [block.strip() for block in body.split("\n\n") if block.strip()]
    fallback_pages = []
    for block in blocks[:4]:
        lines = [line.strip(" -•") for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        fallback_pages.append(
            {
                "heading": lines[0][:24],
                "bullets": lines[1:4] or [lines[0]],
                "footer": package.get("topic", ""),
            }
        )
    return fallback_pages or [{"heading": package.get("title", "小红书笔记"), "bullets": ["补充你的重点内容"], "footer": ""}]


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Xiaohongshu note images from a JSON package.")
    parser.add_argument("package", help="Path to post.json")
    parser.add_argument("--outdir", default=None, help="Output directory, default: sibling images/")
    args = parser.parse_args()

    package_path = Path(args.package).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve() if args.outdir else package_path.parent / "images"
    outdir.mkdir(parents=True, exist_ok=True)

    package = load_package(package_path)
    pages = normalize_pages(package)

    cover_path = outdir / "cover.png"
    make_cover(package, cover_path)

    image_paths = [str(cover_path)]
    total = len(pages)
    for idx, page in enumerate(pages, start=1):
        out_path = outdir / f"page-{idx:02d}.png"
        make_page(page, idx, total, out_path)
        image_paths.append(str(out_path))

    manifest = {
        "package": str(package_path),
        "image_dir": str(outdir),
        "images": image_paths,
    }
    with (outdir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
