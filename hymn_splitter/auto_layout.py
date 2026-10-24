from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image


class AutoLayoutError(ValueError):
    """Raised when a score image cannot be split automatically."""


def _safe_stem(path: Path) -> str:
    stem = re.sub(r"[\\/:*?\"<>|]+", "-", path.stem).strip(" .-")
    return stem or "未命名诗歌"


def _split_title(stem: str) -> tuple[str, str]:
    match = re.match(r"^\s*(\d{1,4})[\s._-]+(.+?)\s*$", stem)
    if match:
        return match.group(1), match.group(2).strip()
    match = re.match(r"^\s*(\d{1,4})(.+?)\s*$", stem)
    if match:
        return match.group(1), match.group(2).strip()
    return "", stem


def _row_counts(gray: Image.Image, threshold: int = 185) -> list[int]:
    """Return dark-pixel counts for each scan line."""
    width, height = gray.size
    margin = max(8, int(width * 0.035))
    left = margin
    right = max(left + 1, width - margin)
    pixels = gray.load()
    counts: list[int] = []
    for y in range(height):
        count = 0
        for x in range(left, right):
            if pixels[x, y] < threshold:
                count += 1
        counts.append(count)
    return counts


def _find_runs(
    counts: list[int],
    *,
    min_ink: int,
    merge_gap: int = 7,
) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    last_active = -1
    for y, count in enumerate(counts):
        active = count >= min_ink
        if active:
            if start is None:
                start = y
            last_active = y
        elif start is not None and y - last_active > merge_gap:
            runs.append((start, last_active))
            start = None
    if start is not None:
        runs.append((start, last_active))
    return runs


def _measure_run(
    gray: Image.Image,
    run: tuple[int, int],
    threshold: int = 185,
) -> dict[str, Any]:
    top, bottom = run
    height = bottom - top + 1
    width = gray.width
    crop = gray.crop((0, top, width, bottom + 1))
    pixels = crop.load()
    ink_columns = 0
    tall_columns = 0
    max_vertical = 0
    left = width
    right = 0

    for x in range(width):
        column_ink = 0
        longest = 0
        current = 0
        for y in range(height):
            if pixels[x, y] < threshold:
                column_ink += 1
                current += 1
                if current > longest:
                    longest = current
            else:
                current = 0
        if column_ink:
            ink_columns += 1
            if x < left:
                left = x
            if x > right:
                right = x
        if longest > max_vertical:
            max_vertical = longest
        if height >= 24 and longest >= max(12, int(height * 0.68)):
            tall_columns += 1

    return {
        "top": top,
        "bottom": bottom,
        "height": height,
        "ink_columns": ink_columns,
        "coverage": ink_columns / max(1, width),
        "span_ratio": max(0, right - left + 1) / max(1, width),
        "left": left if left < width else 0,
        "right": right,
        "max_vertical": max_vertical,
        "max_vertical_ratio": max_vertical / max(1, height),
        "tall_columns": tall_columns,
    }


def _looks_like_note_run(metrics: dict[str, Any], image_width: int) -> bool:
    height = int(metrics["height"])
    if height < 20:
        return False
    tall_columns = int(metrics["tall_columns"])
    ratio = float(metrics["max_vertical_ratio"])
    # Bar lines are the most stable visual difference between a numbered
    # staff and the Chinese lyric line underneath it.
    barline_threshold = max(3, int(image_width / 420))
    if tall_columns >= barline_threshold and ratio >= 0.7:
        return True
    return tall_columns >= max(6, int(image_width / 240)) and ratio >= 0.58


def _looks_like_lyric_run(metrics: dict[str, Any]) -> bool:
    height = int(metrics["height"])
    if not 30 <= height <= 125:
        return False
    # Numbered notation rows are much airier than the Chinese lyric lines:
    # their dark pixels occupy a smaller fraction of the scan width.
    if float(metrics["coverage"]) < 0.28:
        return False
    if int(metrics["ink_columns"]) < 40:
        return False
    return True


def _group_lyric_runs(
    runs: list[dict[str, Any]],
    *,
    image_width: int,
) -> list[list[dict[str, Any]]]:
    lyric_runs = [
        item
        for item in runs
        if _looks_like_lyric_run(item)
    ]
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for item in lyric_runs:
        if not current:
            current = [item]
            continue
        previous = current[-1]
        gap = int(item["top"]) - int(previous["bottom"])
        previous_height = int(previous["height"])
        current_height = int(item["height"])
        similar = 0.52 <= current_height / max(1, previous_height) <= 1.9
        if gap <= 75 and similar:
            current.append(item)
        else:
            if len(current) >= 2:
                groups.extend(_split_mixed_group(current))
            current = [item]
    if len(current) >= 2:
        groups.extend(_split_mixed_group(current))
    return [group for group in groups if len(group) >= 2]


def _split_mixed_group(group: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Split lyric bands when a staff run touches the next lyric line."""
    if len(group) < 2:
        return [group]
    split_indices: list[int] = []
    for index in range(1, len(group)):
        lookahead = group[index + 1 : index + 5]
        if not lookahead:
            continue
        coverages = sorted(float(item["coverage"]) for item in lookahead)
        heights = sorted(int(item["height"]) for item in lookahead)
        median_coverage = coverages[len(coverages) // 2]
        median_height = heights[len(heights) // 2]
        current = group[index]
        coverage = float(current["coverage"])
        height = int(current["height"])
        if (
            coverage <= median_coverage * 0.78
            or height >= median_height * 1.12
        ):
            split_indices.append(index)

    if not split_indices:
        return [_drop_leading_staff_run(group)]

    parts: list[list[dict[str, Any]]] = []
    start = 0
    for index in split_indices:
        if index > start:
            parts.append(group[start:index])
        start = index
    parts.append(group[start:])
    return [_drop_leading_staff_run(part) for part in parts if part]


def _drop_leading_staff_run(group: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove a dense staff run that touched the first lyric line.

    Some scans have a staff whose bar line reaches the first lyric row, so
    the projection merges both into one band. The following lyric rows are
    much denser than the merged band; that contrast gives us a safe cleanup.
    """
    if len(group) < 2:
        return group
    rest = group[1:]
    rest_coverages = sorted(float(item["coverage"]) for item in rest)
    rest_heights = sorted(int(item["height"]) for item in rest)
    middle = len(rest) // 2
    median_coverage = rest_coverages[middle]
    median_height = rest_heights[middle]
    first = group[0]
    first_coverage = float(first["coverage"])
    first_height = int(first["height"])
    coverage_drop = first_coverage < median_coverage * 0.76
    height_growth = first_height > median_height * 1.08
    if coverage_drop or height_growth:
        return rest
    return group


def _merge_note_runs(
    runs: list[dict[str, Any]],
    *,
    lyric_top: int,
    lower_bound: int,
    image_width: int,
) -> tuple[int, int] | None:
    candidates: list[dict[str, Any]] = []
    for item in runs:
        top = int(item["top"])
        bottom = int(item["bottom"])
        if bottom >= lyric_top:
            continue
        if bottom < lower_bound:
            continue
        if lyric_top - bottom > 210:
            continue
        if _looks_like_lyric_run(item) and not _looks_like_note_run(item, image_width):
            # A lyric-looking run immediately above the group is usually a
            # credit/header line. Keep it only when it has staff-like marks.
            continue
        candidates.append(item)

    if not candidates:
        return None

    # Keep the actual staff line(s), then reattach nearby chord labels and
    # small marks. This avoids swallowing the key/time-signature line that
    # often sits a little higher in the page header.
    core = [
        item
        for item in candidates
        if int(item["height"]) >= 25 and float(item["span_ratio"]) >= 0.35
    ]
    if not core:
        core = [
            item
            for item in candidates
            if int(item["height"]) >= 18 and float(item["span_ratio"]) >= 0.2
        ]
    if not core:
        core = candidates

    selected = list(core)
    changed = True
    while changed:
        changed = False
        for item in candidates:
            if item in selected:
                continue
            if int(item["height"]) > 28 or float(item["span_ratio"]) < 0.35:
                continue
            selected_top = min(int(entry["top"]) for entry in selected)
            selected_bottom = max(int(entry["bottom"]) for entry in selected)
            top = int(item["top"])
            bottom = int(item["bottom"])
            gap = min(abs(selected_top - bottom), abs(top - selected_bottom))
            if gap <= 60:
                selected.append(item)
                changed = True

    top = min(int(item["top"]) for item in selected)
    bottom = max(int(item["bottom"]) for item in selected)
    return top, min(bottom, lyric_top - 2)


def _make_page_label(width: int, header_bottom: int) -> dict[str, Any]:
    font_size = max(30, min(58, int(width / 58)))
    return {
        "enabled": True,
        "position": [max(80, int(width * 0.88)), max(50, int(header_bottom * 0.78))],
        "compact_position": [max(80, int(width * 0.93)), max(34, font_size)],
        "font": "C:/Windows/Fonts/msyhbd.ttc",
        "font_size": font_size,
        "compact_font_size": max(28, int(font_size * 0.82)),
        "color": [45, 45, 45],
        "anchor": "rm",
    }


def _build_auto_config(
    source_path: Path,
    image: Image.Image,
    runs: list[dict[str, Any]],
    *,
    song_number: str = "",
    song_title: str = "",
) -> dict[str, Any]:
    width = image.width
    groups = _group_lyric_runs(runs, image_width=width)
    if not groups:
        raise AutoLayoutError(
            "没有识别到歌词行。请确认图片是清晰的简谱整页图片，"
            "或改用已有的 JSON 布局配置。"
        )

    counts = Counter(len(group) for group in groups)
    viable_counts = {count: frequency for count, frequency in counts.items() if count >= 2}
    if not viable_counts:
        raise AutoLayoutError("识别到的歌词行太少，暂时无法自动分段。")
    first_count = max(
        viable_counts,
        key=lambda count: (viable_counts[count], count),
    )

    main_groups: list[list[dict[str, Any]]] = []
    remaining: list[list[dict[str, Any]]] = []
    started = False
    reached_chorus = False
    for group in groups:
        if not started:
            if len(group) != first_count:
                continue
            started = True
            main_groups.append(group)
        elif not reached_chorus and len(group) == first_count:
            main_groups.append(group)
        else:
            reached_chorus = True
            remaining.append(group)
    if not main_groups:
        raise AutoLayoutError("没有识别到完整的主歌段落。")

    systems: list[dict[str, Any]] = []
    previous_bottom = 0
    for group_index, group in enumerate(main_groups):
        lyric_top = int(group[0]["top"])
        if group_index == 0:
            lower_bound = max(0, lyric_top - 270)
        else:
            lower_bound = previous_bottom + 8
        note_range = _merge_note_runs(
            runs,
            lyric_top=lyric_top,
            lower_bound=lower_bound,
            image_width=width,
        )
        if note_range is None:
            raise AutoLayoutError(
                f"第 {group_index + 1} 组乐谱没有识别到简谱行。"
            )
        note_top, note_bottom = note_range
        note_top = max(0, note_top - 8)
        note_bottom = min(lyric_top - 2, note_bottom + 8)
        lyric_rows = [
            [max(0, int(item["top"]) - 3), min(image.height, int(item["bottom"]) + 4)]
            for item in group
        ]
        systems.append(
            {
                "note_crop": [0, note_top, width, note_bottom],
                "lyric_rows": lyric_rows,
            }
        )
        previous_bottom = max(int(item["bottom"]) for item in group)

    first_note_top = int(systems[0]["note_crop"][1])
    header_bottom = max(40, first_note_top - 10)
    verse_labels = [f"第{index + 1}段" for index in range(first_count)]

    chorus: dict[str, Any] | None = None
    chorus_blocks: list[dict[str, Any]] = []
    last_main_bottom = max(
        (int(item["bottom"]) for group in main_groups for item in group),
        default=0,
    )
    grouped_runs = {
        id(item)
        for group in [*main_groups, *remaining]
        for item in group
    }
    singleton_candidates = [
        item
        for item in runs
        if id(item) not in grouped_runs
        and int(item["top"]) > last_main_bottom + 20
        and _looks_like_lyric_run(item)
        and int(item["height"]) <= 100
        and float(item["coverage"]) >= 0.30
    ]
    chorus_groups = [*remaining, *([item] for item in singleton_candidates)]
    for group in chorus_groups:
        lyric_top = int(group[0]["top"])
        note_range = _merge_note_runs(
            runs,
            lyric_top=lyric_top,
            lower_bound=max(0, lyric_top - 300),
            image_width=width,
        )
        if note_range is None:
            continue
        note_top, note_bottom = note_range
        # A chorus group may contain multiple lyric lines. Keep each line as
        # a block so the engine can render them in sequence.
        for item in group:
            block_top = max(0, note_top - 8)
            block_bottom = min(int(item["top"]) - 2, note_bottom + 8)
            chorus_blocks.append(
                {
                    "note_crop": [0, block_top, width, block_bottom],
                    "lyric_row": [
                        max(0, int(item["top"]) - 3),
                        min(image.height, int(item["bottom"]) + 4),
                    ],
                }
            )
    if chorus_blocks:
        chorus = {"label": "副歌", "blocks": chorus_blocks}

    stem = _safe_stem(source_path)
    detected_number, detected_title = _split_title(stem)
    number = (song_number or detected_number).strip()
    title = (song_title or detected_title or stem).strip()
    prefix = f"{number}-{title}" if number else title

    return {
        "base_dir": str(source_path.parent),
        "source": str(source_path),
        "output_dir": str(source_path.parent / "outputs" / prefix),
        "song": {
            "number": number,
            "title": title,
            "file_prefix": prefix,
        },
        "header_crop": [0, 0, width, header_bottom],
        "page": {
            "width": width,
            "background": [255, 255, 255],
            "bottom_margin": 50,
        },
        "page_label": _make_page_label(width, header_bottom),
        "verse_labels": verse_labels,
        "bold_mode": "none",
        "bold_strength": 0,
        "systems": systems,
        "options": {
            "include_chorus_on_verse_pages": False,
            "make_chorus_page": bool(chorus),
        },
        **({"chorus": chorus} if chorus else {}),
        "_auto_layout": True,
    }


def detect_layout(
    source_path: str | Path,
    *,
    song_number: str = "",
    song_title: str = "",
) -> dict[str, Any]:
    """Detect a common Chinese numbered-score layout from one image.

    The detector intentionally stays conservative. It looks for repeated
    groups of lyric lines and attaches the staff immediately above each group.
    A caller can still use a hand-tuned JSON config when a publisher uses a
    highly unusual layout.
    """
    source_path = Path(source_path).resolve()
    if not source_path.is_file():
        raise AutoLayoutError(f"歌谱图片不存在：{source_path}")
    try:
        image = Image.open(source_path).convert("RGB")
    except Exception as error:
        raise AutoLayoutError(f"无法读取歌谱图片：{error}") from error

    gray = image.convert("L")
    counts = _row_counts(gray)
    min_ink = max(12, int(image.width * 0.012))
    raw_runs = _find_runs(counts, min_ink=min_ink)
    runs = [
        _measure_run(gray, run)
        for run in raw_runs
        if run[1] - run[0] + 1 >= 4
    ]
    return _build_auto_config(
        source_path,
        image,
        runs,
        song_number=song_number,
        song_title=song_title,
    )
