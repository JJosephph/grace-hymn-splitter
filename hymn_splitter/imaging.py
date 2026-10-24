from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


def _rgb(value: list[int] | tuple[int, int, int]) -> tuple[int, int, int]:
    return int(value[0]), int(value[1]), int(value[2])


def _full_width_box(
    image: Image.Image, box: list[int]
) -> tuple[int, int, int, int]:
    if len(box) == 2:
        return 0, int(box[0]), image.width, int(box[1])
    return int(box[0]), int(box[1]), int(box[2]), int(box[3])


def _box_height(box: list[int]) -> int:
    if len(box) == 2:
        return int(box[1]) - int(box[0])
    return int(box[3]) - int(box[1])


def bold_text_region(
    image: Image.Image,
    strength: int = 1,
    threshold: int = 210,
    color: tuple[int, int, int] = (40, 40, 40),
) -> Image.Image:
    """Thicken existing dark text without changing its position."""
    result = image.convert("RGB")
    gray = image.convert("L")
    mask = gray.point(lambda pixel: 255 if pixel < threshold else 0)
    size = max(3, strength * 2 + 1)
    mask = mask.filter(ImageFilter.MaxFilter(size))
    result.paste(color, mask=mask)
    return result


def _load_font(config: dict[str, Any], fallback_size: int) -> ImageFont.FreeTypeFont:
    font_path = Path(
        config.get("font", r"C:\Windows\Fonts\STSONG.TTF")
    ).expanduser()
    if not font_path.exists():
        raise FileNotFoundError(f"font file does not exist: {font_path}")
    return ImageFont.truetype(str(font_path), int(config.get("font_size", fallback_size)))


def _draw_replacement(
    page: Image.Image,
    source: Image.Image,
    system: dict[str, Any],
    verse_index: int,
    page_y: int,
    lyric_box: list[int],
    draw: ImageDraw.ImageDraw,
) -> Image.Image:
    replacement = system["replace"]
    left, top, right, bottom = _full_width_box(source, lyric_box)
    lyric_crop = source.crop((left, top, right, bottom))

    text_left, text_right = replacement["text_area"]
    draw.rectangle(
        (text_left, page_y, text_right, page_y + lyric_crop.height),
        fill=(255, 255, 255),
    )

    verse = replacement["verses"][verse_index]
    first, second = verse["parts"]
    characters = first + second
    if len(characters) != len(replacement["x_centers"]):
        raise ValueError(
            "replacement lyric must contain exactly 11 characters per system"
        )

    font_size = int(replacement.get("font_size", 90))
    font = _load_font(replacement, font_size)
    color = _rgb(replacement.get("color", [40, 40, 40]))
    stroke_width = int(replacement.get("stroke_width", 2))
    y_center = page_y + (top + bottom) / 2 - top
    baseline = page_y + bottom + int(replacement.get("baseline_adjust", 1)) - top

    for character, x_center in zip(characters, replacement["x_centers"]):
        draw.text(
            (x_center, y_center),
            character,
            font=font,
            fill=color,
            anchor="mm",
            stroke_width=stroke_width,
            stroke_fill=color,
        )

    middle_x = replacement.get("middle_punct_x")
    middle = verse.get("middle", "")
    if middle and middle_x is not None:
        draw.text(
            (middle_x, baseline),
            middle,
            font=font,
            fill=color,
            anchor="ms",
            stroke_width=stroke_width,
            stroke_fill=color,
        )

    end_x = replacement.get("end_punct_x")
    end = verse.get("end", "")
    if end and end_x is not None:
        draw.text(
            (end_x, baseline),
            end,
            font=font,
            fill=color,
            anchor="ms",
            stroke_width=stroke_width,
            stroke_fill=color,
        )

    return lyric_crop


def _prepare_lyric_crop(
    page: Image.Image,
    source: Image.Image,
    system: dict[str, Any],
    verse_index: int,
    page_y: int,
    lyric_box: list[int],
    draw: ImageDraw.ImageDraw,
    bold: bool,
    bold_strength: int,
) -> Image.Image:
    if system.get("replace"):
        return _draw_replacement(
            page, source, system, verse_index, page_y, lyric_box, draw
        )

    crop = source.crop(_full_width_box(source, lyric_box))
    if bold:
        crop = bold_text_region(crop, strength=bold_strength)
    return crop


def _paste_block(
    page: Image.Image,
    source: Image.Image,
    note_crop_box: list[int],
    lyric_box: list[int],
    y: int,
    draw: ImageDraw.ImageDraw,
    system: dict[str, Any] | None,
    verse_index: int,
    bold: bool,
    bold_strength: int,
) -> int:
    note_crop = source.crop(tuple(note_crop_box))
    page.paste(note_crop, (0, y))
    y += note_crop.height

    if system is not None and system.get("replace"):
        lyric_crop = source.crop(_full_width_box(source, lyric_box))
        page.paste(lyric_crop, (0, y))
        _draw_replacement(
            page,
            source,
            system,
            verse_index,
            y,
            lyric_box,
            draw,
        )
        return y + lyric_crop.height

    if system is None:
        lyric_crop = source.crop(_full_width_box(source, lyric_box))
        if bold:
            lyric_crop = bold_text_region(lyric_crop, strength=bold_strength)
    else:
        lyric_crop = _prepare_lyric_crop(
            page,
            source,
            system,
            verse_index,
            y,
            lyric_box,
            draw,
            bold,
            bold_strength,
        )

    page.paste(lyric_crop, (0, y))
    return y + lyric_crop.height


def _draw_page_label(
    page: Image.Image,
    draw: ImageDraw.ImageDraw,
    config: dict[str, Any],
    label: str,
) -> None:
    label_config = config.get("page_label", {})
    if not label_config.get("enabled", True):
        return
    position = label_config.get("position", [2660, 355])
    font_path = Path(
        label_config.get("font", r"C:\Windows\Fonts\msyhbd.ttc")
    )
    font = ImageFont.truetype(str(font_path), int(label_config.get("font_size", 52)))
    color = _rgb(label_config.get("color", [40, 40, 40]))
    draw.text(
        tuple(position),
        label,
        font=font,
        fill=color,
        anchor=label_config.get("anchor", "mm"),
    )


def _draw_compact_header(
    page: Image.Image,
    draw: ImageDraw.ImageDraw,
    config: dict[str, Any],
    label: str,
    height: int,
) -> None:
    """Draw a small page marker without repeating the full score header."""
    label_config = config.get("page_label", {})
    if not label_config.get("enabled", True):
        return

    font_path = Path(
        label_config.get("font", r"C:\Windows\Fonts\msyhbd.ttc")
    )
    font_size = int(
        label_config.get(
            "compact_font_size",
            max(26, int(label_config.get("font_size", 46) * 0.82)),
        )
    )
    font = ImageFont.truetype(str(font_path), font_size)
    color = _rgb(label_config.get("color", [40, 40, 40]))
    position = label_config.get(
        "compact_position",
        [max(70, page.width - 80), max(30, height // 2)],
    )
    draw.text(
        tuple(position),
        label,
        font=font,
        fill=color,
        anchor=label_config.get("compact_anchor", label_config.get("anchor", "rm")),
    )

    accent = _rgb(
        label_config.get(
            "compact_accent_color",
            config.get("page", {}).get("accent", [125, 190, 160]),
        )
    )
    line_y = max(8, height - max(7, height // 18))
    draw.line((24, line_y, page.width - 24, line_y), fill=accent, width=2)


def _bold_settings(config: dict[str, Any]) -> tuple[bool, int]:
    mode = str(config.get("bold_mode", "")).strip().lower()
    if not mode:
        mode = "light" if config.get("bold_original_lyrics", False) else "none"
    if mode in {"none", "off", "false", "0"}:
        return False, 0
    if mode in {"strong", "heavy", "2"}:
        return True, max(2, int(config.get("bold_strength", 2)))
    if mode in {"replace", "replacement"}:
        return False, 0
    return True, max(1, int(config.get("bold_strength", 1)))


def _header_strategy(config: dict[str, Any]) -> str:
    return str(
        config.get(
            "header_strategy",
            "full_first_page_then_compact",
        )
    ).strip().lower()


def build_pages(config: dict[str, Any], force_chorus: bool | None = None) -> list[Path]:
    source = Image.open(config["_source_path"]).convert("RGB")
    page_config = config["page"]
    page_width = int(page_config.get("width", source.width))
    background = _rgb(page_config.get("background", [255, 255, 255]))
    bottom_margin = int(page_config.get("bottom_margin", 60))
    bold, bold_strength = _bold_settings(config)
    header_crop = tuple(config["header_crop"])
    header_height = header_crop[3] - header_crop[1]
    header_strategy = _header_strategy(config)
    full_first_page = header_strategy not in {
        "compact",
        "compact_all",
        "none",
    }
    compact_header_height = int(
        config.get(
            "compact_header_height",
            max(92, min(180, int(page_width * 0.065))),
        )
    )

    output_dir: Path = config["_output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = config["song"]["file_prefix"]
    verse_count = int(config["_verse_count"])
    verse_labels = config.get(
        "verse_labels",
        [f"第 {index + 1} 段" for index in range(verse_count)],
    )

    include_chorus = (
        bool(force_chorus)
        if force_chorus is not None
        else bool(config.get("options", {}).get("include_chorus_on_verse_pages", False))
    )
    make_chorus_page = bool(
        config.get("options", {}).get("make_chorus_page", bool(config.get("chorus")))
    )

    outputs: list[Path] = []
    for verse_index in range(verse_count):
        use_full_header = (
            full_first_page
            and verse_index == 0
            and header_strategy != "full"
        ) or header_strategy == "full"
        page_header_height = header_height if use_full_header else compact_header_height
        height = page_header_height + bottom_margin
        for system in config["systems"]:
            note_box = system["note_crop"]
            lyric_box = system["lyric_rows"][verse_index]
            height += (note_box[3] - note_box[1]) + _box_height(lyric_box)
        if include_chorus and config.get("chorus"):
            for block in config["chorus"]["blocks"]:
                note_box = block["note_crop"]
                lyric_box = block["lyric_row"]
                height += (note_box[3] - note_box[1]) + _box_height(lyric_box)

        page = Image.new("RGB", (page_width, height), background)
        draw = ImageDraw.Draw(page)
        if use_full_header:
            page.paste(source.crop(header_crop), (0, 0))
            for mask_box in config.get("header_mask", []):
                draw.rectangle(tuple(mask_box), fill=background)
            _draw_page_label(page, draw, config, verse_labels[verse_index])
        else:
            _draw_compact_header(
                page,
                draw,
                config,
                verse_labels[verse_index],
                page_header_height,
            )

        y = page_header_height
        for system in config["systems"]:
            y = _paste_block(
                page,
                source,
                system["note_crop"],
                system["lyric_rows"][verse_index],
                y,
                draw,
                system,
                verse_index,
                bold,
                bold_strength,
            )

        if include_chorus and config.get("chorus"):
            for block in config["chorus"]["blocks"]:
                y = _paste_block(
                    page,
                    source,
                    block["note_crop"],
                    block["lyric_row"],
                    y,
                    draw,
                    None,
                    verse_index,
                    bold,
                    bold_strength,
                )

        output = output_dir / f"{prefix}-{verse_labels[verse_index]}.png"
        page.save(output, format="PNG", optimize=True)
        outputs.append(output)

    if make_chorus_page and config.get("chorus"):
        page_header_height = compact_header_height
        height = page_header_height + bottom_margin
        for block in config["chorus"]["blocks"]:
            note_box = block["note_crop"]
            lyric_box = block["lyric_row"]
            height += (note_box[3] - note_box[1]) + _box_height(lyric_box)

        page = Image.new("RGB", (page_width, height), background)
        draw = ImageDraw.Draw(page)
        _draw_compact_header(
            page,
            draw,
            config,
            config["chorus"].get("label", "副歌"),
            page_header_height,
        )
        y = page_header_height
        for block in config["chorus"]["blocks"]:
            y = _paste_block(
                page,
                source,
                block["note_crop"],
                block["lyric_row"],
                y,
                draw,
                None,
                0,
                bold,
                bold_strength,
            )
        output = output_dir / f"{prefix}-{config['chorus'].get('label', '副歌')}.png"
        page.save(output, format="PNG", optimize=True)
        outputs.append(output)

    return outputs
