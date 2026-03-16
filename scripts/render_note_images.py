#!/usr/bin/env python3

import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont


CANVAS = (1242, 1660)
MARGIN_X = 96
TOP_Y = 110


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
    image = Image.new("RGB", CANVAS, "#F6F0E8")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((70, 70, 1172, 1590), radius=56, fill="#FFFDF8")
    draw.rounded_rectangle((780, 90, 1120, 230), radius=36, fill="#D85C3A")
    draw.text((835, 132), "小红书", font=pick_font(54, bold=True), fill="#FFF8EF")

    title = package.get("cover", {}).get("title") or package.get("title") or package.get("topic") or "小红书笔记"
    subtitle = package.get("cover", {}).get("subtitle") or "把复杂内容讲清楚"

    accent_y = 330
    draw.rounded_rectangle((MARGIN_X, accent_y, 1090, accent_y + 28), radius=14, fill="#F2C14E")

    title_font = pick_font(96, bold=True)
    subtitle_font = pick_font(46)
    y = 420
    for line in wrap_text(draw, title, title_font, 920):
        draw.text((MARGIN_X, y), line, font=title_font, fill="#1B1B1B")
        bbox = draw.textbbox((MARGIN_X, y), line, font=title_font)
        y = bbox[3] + 22

    y += 18
    y = draw_paragraph(draw, subtitle, (MARGIN_X, y), subtitle_font, 840, "#5C5248", 12)

    card_top = 1040
    card = (MARGIN_X, card_top, 1120, 1450)
    draw.rounded_rectangle(card, radius=42, fill="#FFF2DD")

    body = package.get("body", "")
    preview_lines = []
    for para in [p.strip() for p in body.split("\n") if p.strip()]:
        preview_lines.append(para)
        if len(preview_lines) == 3:
            break
    preview = " / ".join(preview_lines)[:120]
    draw.text((140, 1110), "这篇内容会讲：", font=pick_font(42, bold=True), fill="#A14E2B")
    draw_paragraph(draw, preview or "核心观点、步骤拆解、落地建议", (140, 1180), pick_font(40), 900, "#302923", 10)

    draw.rounded_rectangle((870, 1360, 1090, 1450), radius=30, fill="#1B1B1B")
    image.save(out_path)


def make_page(page: Dict, index: int, total: int, out_path: Path) -> None:
    palette = [
        ("#FCFBF7", "#2A2522", "#C95F47", "#F6E7D7"),
        ("#F8F3EC", "#202123", "#3B7A78", "#DCEEEB"),
        ("#F7F7FA", "#1D2330", "#D9813A", "#F8E5D2"),
    ]
    bg, fg, accent, panel = palette[(index - 1) % len(palette)]
    image = Image.new("RGB", CANVAS, bg)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((80, 80, 1160, 1580), radius=52, fill="#FFFFFF")
    draw.rounded_rectangle((100, 102, 330, 190), radius=28, fill=accent)
    draw.text((145, 126), f"第 {index} 页", font=pick_font(38, bold=True), fill="#FFFFFF")
    draw.text((1005, 128), f"{index}/{total}", font=pick_font(34), fill="#6C6C72")

    heading = page.get("heading") or f"重点 {index}"
    draw_paragraph(draw, heading, (110, 280), pick_font(72, bold=True), 930, fg, 18)

    draw.rounded_rectangle((100, 520, 1140, 1380), radius=40, fill=panel)
    bullet_font = pick_font(46)
    bullet_y = 620
    for bullet in page.get("bullets", [])[:6]:
        text = f"• {bullet}"
        bullet_y = draw_paragraph(draw, text, (150, bullet_y), bullet_font, 860, fg, 12)
        bullet_y += 18

    footer = page.get("footer") or ""
    if footer:
        draw.rounded_rectangle((120, 1430, 1120, 1510), radius=24, fill=accent)
        footer_font = pick_font(34, bold=True)
        footer_width = draw.textbbox((0, 0), footer, font=footer_font)[2]
        footer_x = max(150, math.floor((CANVAS[0] - footer_width) / 2))
        draw.text((footer_x, 1453), footer, font=footer_font, fill="#FFFFFF")

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
