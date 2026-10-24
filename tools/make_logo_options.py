from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "docs" / "logo-options"
SCALE = 4
SIZE = 1024


def px(value: float) -> int:
    return int(round(value * SCALE))


def box(values: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    return tuple(px(value) for value in values)


def rounded(draw: ImageDraw.ImageDraw, values, radius: float, fill) -> None:
    draw.rounded_rectangle(box(values), radius=px(radius), fill=fill)


def ellipse(draw: ImageDraw.ImageDraw, values, fill) -> None:
    draw.ellipse(box(values), fill=fill)


def line(draw: ImageDraw.ImageDraw, points, fill, width: float) -> None:
    draw.line([(px(x), px(y)) for x, y in points], fill=fill, width=px(width), joint="curve")


def polygon(draw: ImageDraw.ImageDraw, points, fill) -> None:
    draw.polygon([(px(x), px(y)) for x, y in points], fill=fill)


def draw_note(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    size: float,
    color,
    *,
    split_color=None,
    split: bool = False,
) -> None:
    head_x = cx - 0.18 * size
    head_y = cy + 0.32 * size
    head_r = 0.22 * size
    ellipse(
        draw,
        (head_x - head_r, head_y - head_r, head_x + head_r, head_y + head_r),
        color,
    )
    line(
        draw,
        [
            (cx + 0.02 * size, cy + 0.25 * size),
            (cx + 0.02 * size, cy - 0.55 * size),
        ],
        color,
        0.12 * size,
    )
    polygon(
        draw,
        [
            (cx + 0.02 * size, cy - 0.55 * size),
            (cx + 0.40 * size, cy - 0.39 * size),
            (cx + 0.29 * size, cy - 0.10 * size),
            (cx + 0.02 * size, cy - 0.25 * size),
        ],
        color,
    )
    if split and split_color is not None:
        line(
            draw,
            [
                (cx - 0.17 * size, cy + 0.02 * size),
                (cx + 0.21 * size, cy - 0.17 * size),
            ],
            split_color,
            0.09 * size,
        )


def icon_canvas(background):
    image = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    rounded(draw, (42, 42, 982, 982), 220, background)
    return image, draw


def logo_01_split_note() -> Image.Image:
    image, draw = icon_canvas("#2563EB")
    rounded(draw, (252, 226, 650, 796), 54, "#93C5FD")
    rounded(draw, (362, 286, 742, 838), 54, "#FFFFFF")
    line(draw, [(552, 320), (552, 806)], "#BFDBFE", 18)
    draw_note(draw, 532, 560, 250, "#2563EB")
    return image


def logo_02_split_beam() -> Image.Image:
    image, draw = icon_canvas("#0F766E")
    for y in (360, 500, 640):
        line(draw, [(245, y), (779, y)], "#99F6E4", 13)
    draw_note(draw, 510, 510, 380, "#FFF7ED", split_color="#0F766E", split=True)
    return image


def logo_03_projection() -> Image.Image:
    image, draw = icon_canvas("#4F46E5")
    rounded(draw, (220, 250, 804, 706), 52, "#FFFFFF")
    rounded(draw, (282, 322, 742, 382), 28, "#4F46E5")
    draw_note(draw, 350, 350, 58, "#FFFFFF")
    rounded(draw, (282, 438, 670, 494), 27, "#C7D2FE")
    rounded(draw, (282, 548, 610, 604), 27, "#C7D2FE")
    line(draw, [(512, 706), (512, 786)], "#FFFFFF", 24)
    rounded(draw, (390, 782, 634, 820), 18, "#FFFFFF")
    return image


def logo_04_open_book() -> Image.Image:
    image, draw = icon_canvas("#E85D4A")
    polygon(draw, [(500, 292), (292, 342), (292, 720), (500, 762)], "#FFF7ED")
    polygon(draw, [(500, 292), (732, 342), (732, 720), (500, 762)], "#FFFFFF")
    line(draw, [(500, 318), (500, 742)], "#E85D4A", 18)
    draw_note(draw, 500, 520, 240, "#E85D4A")
    line(draw, [(360, 620), (452, 632)], "#FDBA74", 18)
    line(draw, [(548, 632), (660, 620)], "#FDBA74", 18)
    return image


def logo_05_segment_stack() -> Image.Image:
    image, draw = icon_canvas("#16A34A")
    rounded(draw, (302, 250, 746, 430), 44, "#BBF7D0")
    rounded(draw, (270, 384, 778, 574), 44, "#FFFFFF")
    rounded(draw, (238, 526, 810, 744), 44, "#FFFFFF")
    draw_note(draw, 360, 470, 120, "#16A34A")
    line(draw, [(472, 438), (686, 438)], "#86EFAC", 18)
    line(draw, [(472, 500), (624, 500)], "#86EFAC", 18)
    line(draw, [(320, 610), (706, 610)], "#86EFAC", 18)
    line(draw, [(320, 672), (598, 672)], "#86EFAC", 18)
    return image


def logo_06_grace_loop() -> Image.Image:
    image, draw = icon_canvas("#1E293B")
    draw.arc(
        box((272, 272, 752, 752)),
        start=22,
        end=338,
        fill="#F59E0B",
        width=px(58),
    )
    line(draw, [(512, 512), (704, 512)], "#F59E0B", 58)
    draw_note(draw, 500, 500, 190, "#FFFFFF", split_color="#1E293B", split=True)
    return image


def save_icon(name: str, image: Image.Image) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"{name}.png"
    image.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(output)
    return output


def font(size: int):
    for candidate in (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def make_contact_sheet(icons: list[tuple[str, Image.Image]]) -> None:
    cell_w, cell_h = 390, 420
    sheet = Image.new("RGB", (cell_w * 3, cell_h * 2), "#F8FAFC")
    draw = ImageDraw.Draw(sheet)
    label_font = font(24)
    for index, (name, icon) in enumerate(icons):
        col = index % 3
        row = index // 3
        x = col * cell_w + (cell_w - 300) // 2
        y = row * cell_h + 34
        thumb = icon.resize((300, 300), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x, y), thumb)
        label = f"{index + 1:02d}  {name}"
        label_box = draw.textbbox((0, 0), label, font=label_font)
        draw.text(
            (col * cell_w + (cell_w - (label_box[2] - label_box[0])) / 2, y + 326),
            label,
            font=label_font,
            fill="#0F172A",
        )
    sheet.save(OUTPUT_DIR / "logo-options.png")


def main() -> None:
    icons = [
        ("split-note", logo_01_split_note()),
        ("split-beam", logo_02_split_beam()),
        ("projection", logo_03_projection()),
        ("open-book", logo_04_open_book()),
        ("segment-stack", logo_05_segment_stack()),
        ("grace-loop", logo_06_grace_loop()),
    ]
    for name, icon in icons:
        save_icon(f"logo-{name}", icon)
    make_contact_sheet(icons)


if __name__ == "__main__":
    main()
