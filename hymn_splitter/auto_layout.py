from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


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


def _separate_color_layers(
    image: Image.Image,
) -> tuple[Image.Image, Image.Image, bool]:
    """Separate colored notation from dark lyric text when a scan uses color."""
    gray = image.convert("L")
    hsv = image.convert("HSV")
    saturation = hsv.getchannel("S")
    colored = saturation.point(lambda pixel: 255 if pixel >= 45 else 0)
    colored_pixels = colored.histogram()[255]
    if colored_pixels < image.width * image.height * 0.003:
        return gray, gray, False

    white = Image.new("L", image.size, 255)
    lyric_gray = Image.composite(white, gray, colored)
    note_gray = Image.composite(gray, white, colored)
    return lyric_gray, note_gray, True


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


def _split_tall_lyric_runs(
    gray: Image.Image,
    runs: list[tuple[int, int]],
    *,
    image_width: int,
) -> list[tuple[int, int]]:
    """Split tightly spaced lyric blocks into individual text rows."""
    counts = _row_counts(gray)
    split_runs: list[tuple[int, int]] = []
    for start, end in runs:
        height = end - start + 1
        if height < 86:
            split_runs.append((start, end))
            continue

        values = counts[start : end + 1]
        threshold = max(14, int(image_width * 0.014))
        valley_candidates = [
            (start + offset, value)
            for offset, value in enumerate(values)
            if 18 <= offset <= height - 18 and value <= threshold
        ]
        if not valley_candidates:
            split_runs.append((start, end))
            continue

        # Collapse adjacent low rows into one valley, then keep the deepest
        # valleys while preserving their vertical order.
        valleys: list[tuple[int, int]] = []
        for position, value in valley_candidates:
            if valleys and position - valleys[-1][0] <= 4:
                if value < valleys[-1][1]:
                    valleys[-1] = (position, value)
            else:
                valleys.append((position, value))

        boundaries: list[int] = []
        for position, _ in valleys:
            if not boundaries or position - boundaries[-1] >= 18:
                boundaries.append(position)
        if not boundaries:
            split_runs.append((start, end))
            continue

        parts: list[tuple[int, int]] = []
        part_start = start
        for boundary in boundaries:
            if boundary - part_start + 1 >= 18:
                parts.append((part_start, boundary - 1))
                part_start = boundary
        if end - part_start + 1 >= 18:
            parts.append((part_start, end))

        if len(parts) >= 2:
            split_runs.extend(parts)
        else:
            split_runs.append((start, end))
    return split_runs


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
    if float(metrics["coverage"]) > 0.78:
        return False
    if int(metrics["ink_columns"]) < 40:
        return False
    return True


def _looks_like_sparse_lyric_run(
    metrics: dict[str, Any],
    *,
    image_width: int,
) -> bool:
    """Recognize a short final lyric line with lighter ink coverage."""
    height = int(metrics["height"])
    if not 45 <= height <= 90:
        return False
    coverage = float(metrics["coverage"])
    if not 0.20 <= coverage < 0.30:
        return False
    if float(metrics["span_ratio"]) < 0.55:
        return False
    return int(metrics["ink_columns"]) >= max(180, int(image_width * 0.20))


def _range_matches_stronger_lyric_band(
    note_range: tuple[int, int],
    candidate: dict[str, Any],
    lyric_runs: list[dict[str, Any]],
) -> bool:
    """Reject a staff band mistakenly treated as a lyric candidate."""
    note_top, note_bottom = note_range
    candidate_tall = int(candidate["tall_columns"])
    for item in lyric_runs:
        if abs(int(item["top"]) - note_top) > 12:
            continue
        if abs(int(item["bottom"]) - note_bottom) > 12:
            continue
        if int(item["tall_columns"]) >= max(12, int(candidate_tall * 1.2)):
            return True
    return False


def _group_lyric_runs(
    runs: list[dict[str, Any]],
    *,
    image_width: int,
    note_runs: list[dict[str, Any]] | None = None,
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
        separated_by_staff = False
        if note_runs:
            gap_start = int(previous["bottom"])
            gap_end = int(item["top"])
            separated_by_staff = any(
                int(note["bottom"]) >= gap_start - 8
                and int(note["top"]) <= gap_end + 8
                and (
                    _looks_like_note_run(note, image_width)
                    or (
                        int(note["height"]) >= 20
                        and float(note["span_ratio"]) >= 0.35
                    )
                )
                for note in note_runs
            )
        if gap <= 75 and similar and not separated_by_staff:
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
    cleaned = list(group)
    while len(cleaned) >= 2:
        first = cleaned[0]
        following = cleaned[1]
        first_tall = int(first["tall_columns"])
        following_tall = int(following["tall_columns"])
        if first_tall <= max(12, int(following_tall * 0.36)):
            cleaned = cleaned[1:]
            continue
        break

    while len(cleaned) >= 2:
        last = cleaned[-1]
        previous = cleaned[-2]
        last_tall = int(last["tall_columns"])
        previous_tall = int(previous["tall_columns"])
        if last_tall <= max(12, int(previous_tall * 0.36)):
            cleaned = cleaned[:-1]
            continue
        break

    if len(cleaned) < 2:
        return cleaned
    rest = cleaned[1:]
    rest_coverages = sorted(float(item["coverage"]) for item in rest)
    rest_heights = sorted(int(item["height"]) for item in rest)
    middle = len(rest) // 2
    median_coverage = rest_coverages[middle]
    median_height = rest_heights[middle]
    first = cleaned[0]
    first_coverage = float(first["coverage"])
    first_height = int(first["height"])
    coverage_drop = first_coverage < median_coverage * 0.76
    height_growth = first_height > median_height * 1.08
    if coverage_drop or height_growth:
        return rest
    return cleaned


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
        if top >= lyric_top:
            continue
        if bottom < lower_bound:
            continue
        if top < lyric_top - 260:
            continue
        candidates.append(item)

    if not candidates:
        return None

    # Use the staff immediately above the lyric line. Choosing the nearest
    # run prevents the previous lyric line from being included in the next
    # chorus crop, which caused duplicated text in multi-system songs.
    note_like = [
        item
        for item in candidates
        if _looks_like_note_run(item, image_width)
    ]
    if not note_like:
        note_like = [
            item
            for item in candidates
            if int(item["height"]) >= 20 and float(item["span_ratio"]) >= 0.25
        ]
    if not note_like:
        note_like = candidates

    anchor = min(
        note_like,
        key=lambda item: (
            max(0, lyric_top - int(item["bottom"])),
            -int(item["top"]),
            -float(item["span_ratio"]),
            -int(item["height"]),
        ),
    )
    selected = [anchor]
    anchor_top = int(anchor["top"])
    anchor_bottom = int(anchor["bottom"])
    for item in note_like:
        if item is anchor:
            continue
        top = int(item["top"])
        bottom = int(item["bottom"])
        gap = min(abs(anchor_top - bottom), abs(top - anchor_bottom))
        if gap <= 18:
            selected.append(item)

    top = min(int(item["top"]) for item in selected)
    bottom = max(int(item["bottom"]) for item in selected)
    return top, min(bottom, lyric_top - 2)


def _find_double_bar_split(
    gray: Image.Image,
    note_run: dict[str, Any],
    *,
    image_width: int,
) -> int | None:
    """Find the center of a double bar inside a numbered staff."""
    top = int(note_run["top"])
    bottom = int(note_run["bottom"])
    height = bottom - top + 1
    if height < 24:
        return None

    crop = gray.crop((0, top, image_width, bottom + 1))
    pixels = crop.load()
    columns: list[int] = []
    for x in range(image_width):
        longest = 0
        current = 0
        for y in range(height):
            if pixels[x, y] < 185:
                current += 1
                longest = max(longest, current)
            else:
                current = 0
        if longest >= height * 0.58:
            columns.append(x)

    clusters: list[list[int]] = []
    for x in columns:
        if clusters and x - clusters[-1][-1] <= 3:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    centers = [
        (sum(cluster) / len(cluster), len(cluster))
        for cluster in clusters
        if len(cluster) >= 2
    ]
    pairs: list[tuple[float, float, float]] = []
    for index in range(len(centers) - 1):
        first, first_width = centers[index]
        second, second_width = centers[index + 1]
        gap = second - first
        if 8 <= gap <= 36:
            pairs.append((first_width + second_width, first, second))
    if not pairs:
        return None

    _, first, second = max(pairs)
    return int((first + second) / 2)


def _ink_ratio(
    gray: Image.Image,
    box: tuple[int, int, int, int],
    *,
    threshold: int = 185,
) -> float:
    """Return the fraction of dark pixels in a crop."""
    left, top, right, bottom = box
    if right <= left or bottom <= top:
        return 0.0
    crop = gray.crop(box)
    pixels = crop.load()
    dark = 0
    for y in range(crop.height):
        for x in range(crop.width):
            if pixels[x, y] < threshold:
                dark += 1
    return dark / max(1, crop.width * crop.height)


def _find_shared_verse_chorus_split(
    note_gray: Image.Image,
    lyric_gray: Image.Image,
    note_runs: list[dict[str, Any]],
    lyric_runs: list[dict[str, Any]],
    *,
    min_rows: int,
    last_main_bottom: int,
    image_height: int,
    image_width: int,
) -> tuple[dict[str, Any], int, list[dict[str, Any]]] | None:
    """Find a final staff shared by the last verse line and the chorus.

    A common hymn-book layout puts the final verse ending and the first
    chorus phrase on the same staff, separated by a double bar. In that
    case the final verse page must use the left side and the chorus page
    must start from the right side.
    """
    candidates = sorted(
        (
            item
            for item in note_runs
            if int(item["top"]) > last_main_bottom + 20
            and int(item["top"]) < last_main_bottom + 720
            and int(item["height"]) >= 20
            and float(item["span_ratio"]) >= 0.35
        ),
        key=lambda item: int(item["top"]),
    )
    for note_run in candidates:
        split_x = _find_double_bar_split(
            note_gray,
            note_run,
            image_width=image_width,
        )
        if split_x is None or not (image_width * 0.12 <= split_x <= image_width * 0.84):
            continue

        note_bottom = int(note_run["bottom"])
        later_lyrics = sorted(
            (
                item
                for item in lyric_runs
                if int(item["top"]) > note_bottom + 20
                and _looks_like_lyric_run(item)
                and 45 <= int(item["height"]) <= 90
                and float(item["coverage"]) >= 0.30
            ),
            key=lambda item: int(item["top"]),
        )
        if len(later_lyrics) < 2:
            continue
        next_chorus_lyric = later_lyrics[1]
        next_note_range = _merge_note_runs(
            note_runs,
            lyric_top=int(next_chorus_lyric["top"]),
            lower_bound=max(0, int(next_chorus_lyric["top"]) - 300),
            image_width=image_width,
        )
        if next_note_range is None:
            continue
        next_note_top = int(next_note_range[0])
        rows = [
            item
            for item in lyric_runs
            if int(item["top"]) >= note_bottom - 8
            and int(item["bottom"]) < next_note_top - 6
            and 28 <= int(item["height"]) <= 115
            and float(item["span_ratio"]) >= 0.15
        ]
        if len(rows) < min_rows:
            continue

        first_row = rows[0]
        row_top = max(0, int(first_row["top"]) - 3)
        row_bottom = min(image_height, int(first_row["bottom"]) + 4)
        left_ink = _ink_ratio(
            lyric_gray,
            (0, row_top, split_x, row_bottom),
        )
        right_ink = _ink_ratio(
            lyric_gray,
            (split_x, row_top, image_width, row_bottom),
        )
        # Both sides must contain real lyric ink. This rejects a final
        # ordinary double bar at the end of a staff, where the right side
        # is mostly whitespace.
        if left_ink < 0.025 or right_ink < 0.025:
            continue

        return note_run, split_x, rows
    return None


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


def _find_content_cutoff(
    runs: list[dict[str, Any]],
    *,
    start_y: int,
    image_width: int,
) -> int | None:
    """Find a thin full-width rule that separates the song from prose notes."""
    for item in runs:
        top = int(item["top"])
        height = int(item["height"])
        if top <= start_y + 20:
            continue
        if height > 24:
            continue
        if float(item["coverage"]) < 0.75:
            continue
        if float(item["span_ratio"]) < 0.8:
            continue
        return top
    return None


def _build_auto_config(
    source_path: Path,
    image: Image.Image,
    lyric_runs: list[dict[str, Any]],
    note_runs: list[dict[str, Any]],
    *,
    separate_note_layer: bool = False,
    song_number: str = "",
    song_title: str = "",
) -> dict[str, Any]:
    width = image.width
    groups = _group_lyric_runs(
        lyric_runs,
        image_width=width,
        note_runs=note_runs if separate_note_layer else None,
    )
    if not groups:
        raise AutoLayoutError(
            "这张歌谱看起来不是多段诗歌，可能只有一段歌词。"
            "自动分段主要面向多段简谱，请确认图片是否选对。"
        )

    counts = Counter(len(group) for group in groups)
    viable_counts = {count: frequency for count, frequency in counts.items() if count >= 2}
    if not viable_counts:
        raise AutoLayoutError(
            "这张歌谱看起来不是多段诗歌，可能只有一段歌词。"
            "自动分段主要面向多段简谱，请确认图片是否选对。"
        )
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

    gray = image.convert("L")
    systems: list[dict[str, Any]] = []
    main_shared_prefix: dict[str, Any] | None = None
    previous_bottom = 0
    for group_index, group in enumerate(main_groups):
        lyric_top = int(group[0]["top"])
        if group_index == 0:
            lower_bound = max(0, lyric_top - 270)
        else:
            lower_bound = previous_bottom + 8
        note_range = _merge_note_runs(
            note_runs,
            lyric_top=lyric_top,
            lower_bound=lower_bound,
            image_width=width,
        )
        if note_range is None:
            raise AutoLayoutError(
                f"第 {group_index + 1} 组乐谱没有识别到简谱行。"
            )
        raw_note_top, raw_note_bottom = note_range
        note_top, note_bottom = note_range
        note_top = max(0, note_top - 8)
        note_bottom = min(lyric_top - 2, note_bottom + 8)
        lyric_rows = [
            [max(0, int(item["top"]) - 3), min(image.height, int(item["bottom"]) + 4)]
            for item in group
        ]
        system_right = width
        if group_index == len(main_groups) - 1:
            note_candidate = min(
                note_runs,
                key=lambda item: (
                    abs(int(item["top"]) - raw_note_top)
                    + abs(int(item["bottom"]) - raw_note_bottom)
                ),
                default=None,
            )
            if (
                note_candidate is not None
                and abs(int(note_candidate["top"]) - raw_note_top) <= 16
                and abs(int(note_candidate["bottom"]) - raw_note_bottom) <= 16
            ):
                split_x = _find_double_bar_split(
                    gray,
                    note_candidate,
                    image_width=width,
                )
                if split_x is not None and width * 0.12 <= split_x <= width * 0.84:
                    first_row = group[0]
                    row_top = max(0, int(first_row["top"]) - 3)
                    row_bottom = min(image.height, int(first_row["bottom"]) + 4)
                    left_ink = _ink_ratio(
                        gray,
                        (0, row_top, split_x, row_bottom),
                    )
                    right_ink = _ink_ratio(
                        gray,
                        (split_x, row_top, width, row_bottom),
                    )
                    later_lyrics = [
                        item
                        for item in lyric_runs
                        if int(item["top"]) > max(
                            int(row["bottom"]) for row in group
                        )
                        + 20
                        and _looks_like_lyric_run(item)
                        and 45 <= int(item["height"]) <= 90
                        and float(item["coverage"]) >= 0.30
                    ]
                    if left_ink >= 0.025 and right_ink >= 0.025 and later_lyrics:
                        system_right = split_x
                        lyric_rows = [
                            [
                                0,
                                max(0, int(item["top"]) - 3),
                                split_x,
                                min(image.height, int(item["bottom"]) + 4),
                            ]
                            for item in group
                        ]
                        main_shared_prefix = {
                            "note_crop": [split_x, note_top, width, note_bottom],
                            "lyric_rows": [
                                [
                                    split_x,
                                    row_top,
                                    width,
                                    row_bottom,
                                ]
                            ],
                        }
        systems.append(
            {
                "note_crop": [0, note_top, system_right, note_bottom],
                "lyric_rows": lyric_rows,
            }
        )
        previous_bottom = max(int(item["bottom"]) for item in group)

    first_note_top = int(systems[0]["note_crop"][1])
    header_bottom = max(40, first_note_top - 10)
    verse_labels = [f"第{index + 1}段" for index in range(first_count)]

    chorus: dict[str, Any] | None = None
    chorus_blocks: list[dict[str, Any]] = (
        [main_shared_prefix] if main_shared_prefix is not None else []
    )
    last_main_bottom = max(
        (int(item["bottom"]) for group in main_groups for item in group),
        default=0,
    )
    shared_split = _find_shared_verse_chorus_split(
        gray,
        gray,
        note_runs,
        lyric_runs,
        min_rows=first_count,
        last_main_bottom=last_main_bottom,
        image_height=image.height,
        image_width=width,
    )
    shared_lyric_ids: set[int] = set()
    if shared_split is not None:
        shared_note, split_x, shared_rows = shared_split
        shared_rows = shared_rows[:first_count]
        shared_note_top = max(0, int(shared_note["top"]) - 8)
        shared_note_bottom = min(
            int(shared_rows[0]["top"]) - 2,
            int(shared_note["bottom"]) + 8,
        )
        systems.append(
            {
                "note_crop": [0, shared_note_top, split_x, shared_note_bottom],
                "lyric_rows": [
                    [
                        0,
                        max(0, int(item["top"]) - 3),
                        split_x,
                        min(image.height, int(item["bottom"]) + 4),
                    ]
                    for item in shared_rows
                ],
            }
        )
        chorus_blocks.append(
            {
                "note_crop": [split_x, shared_note_top, width, shared_note_bottom],
                "lyric_rows": [
                    [
                        split_x,
                        max(0, int(shared_rows[0]["top"]) - 3),
                        width,
                        min(image.height, int(shared_rows[0]["bottom"]) + 4),
                    ]
                ],
            }
        )
        shared_lyric_ids = {id(item) for item in shared_rows}
        last_main_bottom = max(
            last_main_bottom,
            max(int(item["bottom"]) for item in shared_rows),
        )
        remaining = [
            group
            for group in remaining
            if not any(id(item) in shared_lyric_ids for item in group)
        ]

    content_cutoff = _find_content_cutoff(
        lyric_runs,
        start_y=last_main_bottom,
        image_width=width,
    )
    if content_cutoff is not None:
        remaining = [
            group
            for group in remaining
            if int(group[0]["top"]) < content_cutoff
        ]
    grouped_runs = {
        id(item)
        for group in [*main_groups, *remaining]
        for item in group
    }
    grouped_runs.update(shared_lyric_ids)
    singleton_candidates = [
        item
        for item in lyric_runs
        if id(item) not in grouped_runs
        and int(item["top"]) > last_main_bottom + 20
        and (content_cutoff is None or int(item["top"]) < content_cutoff)
        and 45 <= int(item["height"]) <= 90
        and (
            (
                _looks_like_lyric_run(item)
                and float(item["coverage"]) >= 0.30
            )
            or _looks_like_sparse_lyric_run(item, image_width=width)
        )
    ]
    chorus_groups = [*remaining, *([item] for item in singleton_candidates)]
    for group in chorus_groups:
        lyric_top = int(group[0]["top"])
        note_range = _merge_note_runs(
            note_runs,
            lyric_top=lyric_top,
            lower_bound=max(0, lyric_top - 300),
            image_width=width,
        )
        if note_range is None:
            continue
        if _range_matches_stronger_lyric_band(note_range, group[0], lyric_runs):
            continue
        note_top, note_bottom = note_range
        block_top = max(0, note_top - 8)
        block_bottom = min(lyric_top - 2, note_bottom + 8)
        if block_bottom - block_top < 35:
            continue
        lyric_rows = [
            [
                max(0, int(item["top"]) - 3),
                min(image.height, int(item["bottom"]) + 4),
            ]
            for item in group
        ]
        chorus_blocks.append(
            {
                "note_crop": [0, block_top, width, block_bottom],
                "lyric_rows": lyric_rows,
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
        image = ImageOps.exif_transpose(Image.open(source_path)).convert("RGB")
    except Exception as error:
        raise AutoLayoutError(f"无法读取歌谱图片：{error}") from error

    lyric_gray, note_gray, has_separate_note_layer = _separate_color_layers(image)
    min_ink = max(12, int(image.width * 0.012))
    lyric_raw_runs = _find_runs(_row_counts(lyric_gray), min_ink=min_ink)
    note_raw_runs = _find_runs(_row_counts(note_gray), min_ink=min_ink)
    lyric_raw_runs = _split_tall_lyric_runs(
        lyric_gray,
        lyric_raw_runs,
        image_width=image.width,
    )
    lyric_runs = [
        _measure_run(lyric_gray, run)
        for run in lyric_raw_runs
        if run[1] - run[0] + 1 >= 4
    ]
    note_runs = [
        _measure_run(note_gray, run)
        for run in note_raw_runs
        if run[1] - run[0] + 1 >= 4
    ]
    return _build_auto_config(
        source_path,
        image,
        lyric_runs,
        note_runs,
        separate_note_layer=has_separate_note_layer,
        song_number=song_number,
        song_title=song_title,
    )
