from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.make_logo_options import (
    SCALE,
    SIZE,
    draw_note,
    icon_canvas,
    line,
    polygon,
    px,
    rounded,
)


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "docs" / "logo-options"
CORAL = "#E85D4A"
CREAM = "#FFF7ED"
WHITE = "#FFFFFF"
ACCENT = "#FDBA74"
INK = "#334155"


def chinese_font(size: float, bold: bool = True):
    font_path = "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"
    return ImageFont.truetype(font_path, px(size))


def centered_text(draw: ImageDraw.ImageDraw, text: str, cx: float, cy: float, size: float, fill, bold=True):
    draw.text(
        (px(cx), px(cy)),
        text,
        font=chinese_font(size, bold),
        fill=fill,
        anchor="mm",
    )


def transformed(points, cx: float, cy: float, scale: float):
    return [(cx + (x - 500) * scale, cy + (y - 500) * scale) for x, y in points]


def draw_open_book_mark(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float) -> None:
    polygon(
        draw,
        transformed([(500, 292), (292, 342), (292, 720), (500, 762)], cx, cy, scale),
        CREAM,
    )
    polygon(
        draw,
        transformed([(500, 292), (732, 342), (732, 720), (500, 762)], cx, cy, scale),
        WHITE,
    )
    line(
        draw,
        transformed([(500, 318), (500, 742)], cx, cy, scale),
        CORAL,
        18 * scale,
    )
    draw_note(draw, cx, cy + 20 * scale, 240 * scale, CORAL)
    line(
        draw,
        transformed([(360, 620), (452, 632)], cx, cy, scale),
        ACCENT,
        18 * scale,
    )
    line(
        draw,
        transformed([(548, 632), (660, 620)], cx, cy, scale),
        ACCENT,
        18 * scale,
    )


def text_below() -> Image.Image:
    image, draw = icon_canvas(CORAL)
    draw_open_book_mark(draw, 512, 410, 0.72)
    centered_text(draw, "恩典", 512, 718, 132, WHITE)
    centered_text(draw, "歌谱转换PPT大图", 512, 850, 40, CREAM, bold=False)
    return image


def text_pill() -> Image.Image:
    image, draw = icon_canvas(CORAL)
    draw_open_book_mark(draw, 512, 400, 0.70)
    rounded(draw, (206, 720, 818, 904), 92, CREAM)
    centered_text(draw, "恩典", 512, 812, 112, CORAL)
    return image


def text_minimal() -> Image.Image:
    image, draw = icon_canvas(CORAL)
    draw_open_book_mark(draw, 512, 470, 0.94)
    centered_text(draw, "恩典", 512, 852, 86, WHITE)
    return image


def text_stacked() -> Image.Image:
    image, draw = icon_canvas(CORAL)
    draw_open_book_mark(draw, 512, 380, 0.68)
    centered_text(draw, "恩典", 512, 694, 126, WHITE)
    centered_text(draw, "歌谱", 512, 818, 76, CREAM)
    return image


def text_seal() -> Image.Image:
    image, draw = icon_canvas(CORAL)
    draw.ellipse(box((214, 172, 810, 768)), fill=CREAM)
    draw_open_book_mark(draw, 512, 390, 0.58)
    centered_text(draw, "恩典", 512, 662, 104, CORAL)
    centered_text(draw, "GRACE HYMN", 512, 760, 26, "#F97316", bold=False)
    return image


def horizontal_lockup() -> Image.Image:
    width, height = 1600, 600
    image = Image.new("RGBA", (px(width), px(height)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    rounded(draw, (0, 0, width, height), 96, "#FFF7F3")
    rounded(draw, (78, 88, 508, 518), 104, CORAL)
    draw_open_book_mark(draw, 293, 303, 0.50)
    draw.text(
        (px(590), px(280)),
        "恩典",
        font=chinese_font(140, True),
        fill=CORAL,
        anchor="lm",
    )
    draw.text(
        (px(594), px(410)),
        "歌谱转换PPT大图",
        font=chinese_font(46, False),
        fill=INK,
        anchor="lm",
    )
    return image


def box(values):
    return tuple(px(value) for value in values)


def save(name: str, image: Image.Image) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"{name}.png"
    if image.width == SIZE * SCALE and image.height == SIZE * SCALE:
        image = image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    else:
        image = image.resize((image.width // SCALE, image.height // SCALE), Image.Resampling.LANCZOS)
    image.save(output)


def contact_sheet(items: list[tuple[str, str, Image.Image]]) -> None:
    cell_w, cell_h = 520, 560
    sheet = Image.new("RGB", (cell_w * 3, cell_h * 2), "#F8FAFC")
    draw = ImageDraw.Draw(sheet)
    label_font = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 24)
    for index, (_filename, label, icon) in enumerate(items):
        col = index % 3
        row = index // 3
        thumb = ImageOps.contain(icon, (430, 360), Image.Resampling.LANCZOS)
        x = col * cell_w + (cell_w - thumb.width) // 2
        y = row * cell_h + 62
        if thumb.mode == "RGBA":
            sheet.paste(thumb, (x, y), thumb)
        else:
            sheet.paste(thumb, (x, y))
        display_label = f"{index + 1:02d}  {label}"
        label_box = draw.textbbox((0, 0), display_label, font=label_font)
        draw.text(
            (col * cell_w + (cell_w - (label_box[2] - label_box[0])) / 2, row * cell_h + 470),
            display_label,
            font=label_font,
            fill="#0F172A",
        )
    sheet.save(OUTPUT_DIR / "logo-04-text-options.png")


def main() -> None:
    items = [
        ("text-below", "文字下方", text_below()),
        ("text-pill", "恩典徽章", text_pill()),
        ("text-minimal", "极简版", text_minimal()),
        ("text-stacked", "上下排列", text_stacked()),
        ("text-seal", "圆形印章", text_seal()),
        ("horizontal-lockup", "横向组合", horizontal_lockup()),
    ]
    for filename, _label, image in items:
        save(f"logo-04-{filename}", image)
    contact_sheet(items)


if __name__ == "__main__":
    main()
