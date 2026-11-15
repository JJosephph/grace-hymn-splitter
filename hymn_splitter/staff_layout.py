from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image

"""Detect hymn pages that combine a five-line staff, jianpu and lyrics.

Analysis runs on a width-normalised copy of the page, so the same rules cover
a 500 px screenshot and a 3000 px scan.  Layout is recovered in three steps:
locate the staves, cluster square Chinese glyphs into text rows, then group
each staff pair into one score system with its verse rows.
"""

ANALYSIS_WIDTH = 1600


def _otsu(gray: Image.Image) -> int:
    hist = gray.histogram()
    total = sum(hist)
    sum_all = sum(index * hist[index] for index in range(256))
    sum_b = 0
    weight_b = 0
    best = 0
    threshold = 128
    for value in range(256):
        weight_b += hist[value]
        if weight_b == 0:
            continue
        weight_f = total - weight_b
        if weight_f == 0:
            break
        sum_b += value * hist[value]
        mean_b = sum_b / weight_b
        mean_f = (sum_all - sum_b) / weight_f
        variance = weight_b * weight_f * (mean_b - mean_f) ** 2
        if variance > best:
            best = variance
            threshold = value
    return threshold


def _binary(gray: Image.Image, threshold: int) -> bytes:
    return gray.point(lambda pixel: 1 if pixel < threshold else 0).tobytes()


def _components(
    data: bytes,
    width: int,
    height: int,
) -> list[list[int]]:
    """Connected components via scan-line runs (8-connected)."""
    parent: list[int] = []
    boxes: list[list[int]] = []

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(first: int, second: int) -> None:
        root_a, root_b = find(first), find(second)
        if root_a != root_b:
            parent[root_b] = root_a

    previous: list[tuple[int, int, int]] = []
    for y in range(height):
        row = data[y * width : (y + 1) * width]
        runs: list[tuple[int, int]] = []
        start = -1
        for x, value in enumerate(row):
            if value:
                if start < 0:
                    start = x
            elif start >= 0:
                runs.append((start, x - 1))
                start = -1
        if start >= 0:
            runs.append((start, width - 1))

        current: list[tuple[int, int, int]] = []
        for start, end in runs:
            matched: list[int] = []
            for prev_start, prev_end, label in previous:
                if prev_end < start - 1:
                    continue
                if prev_start > end + 1:
                    break
                matched.append(label)
            if matched:
                label = matched[0]
                for other in matched[1:]:
                    union(label, other)
                label = find(label)
            else:
                label = len(parent)
                parent.append(label)
                boxes.append([start, y, end, y, 0])
            box = boxes[label]
            if start < box[0]:
                box[0] = start
            if end > box[2]:
                box[2] = end
            if y < box[1]:
                box[1] = y
            if y > box[3]:
                box[3] = y
            box[4] += end - start + 1
            current.append((start, end, label))
        previous = current

    merged: dict[int, list[int]] = {}
    for index, box in enumerate(boxes):
        root = find(index)
        target = merged.get(root)
        if target is None:
            merged[root] = box[:]
        else:
            target[0] = min(target[0], box[0])
            target[1] = min(target[1], box[1])
            target[2] = max(target[2], box[2])
            target[3] = max(target[3], box[3])
            target[4] += box[4]
    return list(merged.values())


def _staff_bands(
    data: bytes,
    width: int,
    height: int,
) -> list[tuple[int, int]]:
    """Locate five-line staves by rows that contain long horizontal runs."""
    candidates: list[int] = []
    for y in range(height):
        row = data[y * width : (y + 1) * width]
        run = longest = ink = 0
        for value in row:
            if value:
                run += 1
                ink += 1
            else:
                run = 0
            if run > longest:
                longest = run
        if longest >= width * 0.10 and ink >= width * 0.05:
            candidates.append(y)

    bands: list[list[int]] = []
    merge_gap = max(3, int(height * 0.02))
    for y in candidates:
        if bands and y - bands[-1][1] <= merge_gap:
            bands[-1][1] = y
        else:
            bands.append([y, y])
    return [
        (top, bottom)
        for top, bottom in bands
        if int(height * 0.008) <= bottom - top + 1 <= int(height * 0.065)
    ]


def _text_rows(
    components: list[list[int]],
    *,
    width: int,
) -> list[dict[str, Any]]:
    """Cluster square-ish glyph boxes into horizontal text rows."""
    glyphs: list[list[int]] = []
    min_height = max(12, int(width * 0.010))
    max_height = max(min_height + 4, int(width * 0.040))
    min_width = max(6, int(width * 0.005))
    for box in components:
        box_width = box[2] - box[0] + 1
        box_height = box[3] - box[1] + 1
        if not min_height <= box_height <= max_height:
            continue
        aspect = box_width / box_height
        if not 0.55 <= aspect <= 1.80:
            continue
        if box_width < min_width:
            continue
        if box[4] < 0.20 * box_width * box_height:
            continue
        glyphs.append(box)

    heights = sorted(box[3] - box[1] + 1 for box in glyphs)
    median_height = float(heights[len(heights) // 2]) if heights else 10.0
    merge_gap = max(4.0, median_height * 0.20)

    glyphs.sort(key=lambda box: (box[1] + box[3]) / 2)
    clusters: list[dict[str, Any]] = []
    for box in glyphs:
        center = (box[1] + box[3]) / 2
        if clusters and center - clusters[-1]["last"] <= merge_gap:
            clusters[-1]["boxes"].append(box)
            clusters[-1]["last"] = center
        else:
            clusters.append({"boxes": [box], "last": center})

    rows: list[dict[str, Any]] = []
    for cluster in clusters:
        boxes = cluster["boxes"]
        if len(boxes) < 3:
            continue
        aspects = sorted(
            (box[2] - box[0] + 1) / (box[3] - box[1] + 1) for box in boxes
        )
        narrow = [aspect for aspect in aspects if aspect <= 1.30]
        rows.append(
            {
                "center": sum((box[1] + box[3]) / 2 for box in boxes) / len(boxes),
                "top": min(box[1] for box in boxes),
                "bottom": max(box[3] for box in boxes),
                "count": len(boxes),
                "square_ratio": sum(
                    1 for aspect in aspects if 0.80 <= aspect <= 1.25
                )
                / len(aspects),
                "median_aspect": narrow[len(narrow) // 2] if narrow else aspects[0],
            }
        )
    return rows


def _is_note_row(row: dict[str, Any]) -> bool:
    """Jianpu digits and chord symbols are narrow; Chinese glyphs are square."""
    return (
        float(row["square_ratio"]) < 0.62
        or float(row["median_aspect"]) < 0.80
    )


def _pair_staves(
    staves: list[tuple[int, int]],
) -> list[tuple[tuple[int, int], tuple[int, int] | None]]:
    """Group staves into systems by separating internal from inter-system gaps."""
    if not staves:
        return []
    if len(staves) == 1:
        return [(staves[0], None)]

    gaps = [
        staves[index + 1][0] - staves[index][1]
        for index in range(len(staves) - 1)
    ]
    unique = sorted({gap for gap in gaps if gap > 0})
    threshold: float | None = None
    if len(unique) >= 2:
        best_ratio = 1.0
        split: tuple[int, int] | None = None
        for small, large in zip(unique, unique[1:]):
            ratio = large / small
            if ratio > best_ratio:
                best_ratio = ratio
                split = (small, large)
        if split is not None and best_ratio >= 1.45:
            threshold = math.sqrt(split[0] * split[1])

    systems: list[tuple[tuple[int, int], tuple[int, int] | None]] = []
    index = 0
    while index < len(staves):
        paired = (
            threshold is not None
            and index + 1 < len(staves)
            and gaps[index] >= threshold
        )
        if paired:
            systems.append((staves[index], staves[index + 1]))
            index += 2
        else:
            systems.append((staves[index], None))
            index += 1
    return systems


def _row_pitch(rows: list[dict[str, Any]]) -> float:
    centers = sorted(float(row["center"]) for row in rows)
    gaps = [
        second - first
        for first, second in zip(centers, centers[1:])
        if 4 < second - first < 400
    ]
    if not gaps:
        return 44.0
    gaps.sort()
    return gaps[len(gaps) // 2]


def _snap_boundary(
    profile: list[int],
    *,
    target: int,
    lower: int,
    upper: int,
) -> int:
    """Move a slice boundary onto the quietest nearby row."""
    span = max(2, int((upper - lower) * 0.25))
    low = max(lower, target - span)
    high = min(upper, target + span)
    if high <= low:
        return target
    return min(range(low, high + 1), key=lambda y: (profile[y], abs(y - target)))


def _slice_rows(
    rows: list[dict[str, Any]],
    *,
    profile: list[int],
    pitch: float,
    image_height: int,
) -> list[list[int]]:
    """Turn clustered rows into non-overlapping crop bands."""
    ordered = sorted(rows, key=lambda row: float(row["center"]))
    boundaries: list[int] = []
    for previous, current in zip(ordered, ordered[1:]):
        boundaries.append(
            _snap_boundary(
                profile,
                target=(int(previous["bottom"]) + int(current["top"])) // 2,
                lower=int(previous["bottom"]) - int(pitch * 0.3),
                upper=int(current["top"]) + int(pitch * 0.3),
            )
        )
    edges = [
        max(0, int(ordered[0]["top"]) - int(pitch * 0.22)),
        *boundaries,
        min(image_height, int(ordered[-1]["bottom"]) + int(pitch * 0.22)),
    ]
    if any(edges[index + 1] <= edges[index] for index in range(len(edges) - 1)):
        return []
    return [[edges[index], edges[index + 1]] for index in range(len(edges) - 1)]


def _reslice_rows(
    rows: list[list[int]],
    *,
    count: int,
) -> list[list[int]]:
    """Fallback: re-cut a merged lyric block into evenly spaced rows."""
    top = int(rows[0][0])
    bottom = int(rows[-1][1])
    step = (bottom - top) / count
    return [
        [int(top + step * index), int(top + step * (index + 1))]
        for index in range(count)
    ]


def _scale_point(value: float, scale: float) -> int:
    return int(round(value * scale))


def detect_staff_layout(
    image: Image.Image,
    source_path: Path,
    *,
    song_number: str = "",
    song_title: str = "",
) -> dict[str, Any] | None:
    """Return a layout config when the page uses five-line staves."""
    original_width, original_height = image.size
    scale = ANALYSIS_WIDTH / original_width
    analysis = image.convert("L").resize(
        (ANALYSIS_WIDTH, max(1, round(original_height * scale))),
        Image.LANCZOS,
    )
    width, height = analysis.size
    threshold = min(205, max(185, _otsu(analysis) + 20))
    data = _binary(analysis, threshold)
    staves = _staff_bands(data, width, height)
    if len(staves) < 2:
        return None

    rows = _text_rows(_components(data, width, height), width=width)
    if len(rows) < 2:
        return None

    profile = [
        sum(data[y * width : (y + 1) * width]) for y in range(height)
    ]
    width_scale = original_width / width
    height_scale = original_height / height

    blocks: list[dict[str, Any]] = []
    for top_staff, bottom_staff in _pair_staves(staves):
        region_top = top_staff[1] + 1
        if bottom_staff is None:
            limit = height - 1
            for other_top, _ in staves:
                if other_top > top_staff[1]:
                    limit = other_top - 1
                    break
            region_bottom = limit
        else:
            region_bottom = bottom_staff[0] - 1

        inside = [
            row
            for row in rows
            if region_top < float(row["center"]) < region_bottom
        ]
        lyric_rows = [row for row in inside if not _is_note_row(row)]
        if not lyric_rows:
            continue
        pitch = _row_pitch(lyric_rows)
        slices = _slice_rows(
            lyric_rows,
            profile=profile,
            pitch=pitch,
            image_height=height,
        )
        if not slices:
            continue

        staff_height = top_staff[1] - top_staff[0] + 1
        chord_rows = [
            row
            for row in rows
            if top_staff[0] - max(8, int(pitch * 1.9))
            < float(row["center"])
            < top_staff[0] - staff_height * 0.15
            and _is_note_row(row)
        ]
        note_top = (
            min(int(row["top"]) for row in chord_rows) - 4
            if chord_rows
            else top_staff[0] - int(staff_height * 0.45)
        )
        note_top = max(0, note_top)
        note_bottom = max(note_top + 8, slices[0][0] - 1)

        tail_crops: list[list[int]] = []
        if bottom_staff is not None:
            tail_top = slices[-1][1] + 1
            tail_bottom = min(
                height,
                bottom_staff[1] + int(staff_height * 0.30),
            )
            if tail_bottom - tail_top >= 8:
                tail_crops.append(
                    [
                        0,
                        tail_top,
                        width,
                        tail_bottom,
                    ]
                )

        blocks.append(
            {
                "_note_top": note_top,
                "_note_bottom": note_bottom,
                "_rows": slices,
                "_tail": tail_crops,
            }
        )

    if len(blocks) < 2:
        return None

    counts = [len(block["_rows"]) for block in blocks]
    frequency = Counter(counts)
    verse_count = max(frequency, key=lambda count: (frequency[count], count))
    if verse_count < 2:
        return None

    chorus_limit = max(1, int(round(verse_count * 0.6)))
    verse_blocks: list[dict[str, Any]] = []
    chorus_blocks: list[dict[str, Any]] = []
    for block in blocks:
        rows = block["_rows"]
        if len(rows) == verse_count:
            target = verse_blocks
        elif len(rows) < chorus_limit:
            target = chorus_blocks
        else:
            block["_rows"] = _reslice_rows(rows, count=verse_count)
            target = verse_blocks
        target.append(block)

    if len(verse_blocks) < 2:
        return None

    first_note_top = int(verse_blocks[0]["_note_top"])
    header_bottom = max(
        1,
        _snap_boundary(
            profile,
            target=first_note_top - 3,
            lower=max(1, first_note_top - int(height * 0.02)),
            upper=max(2, first_note_top - 1),
        ),
    )

    def scaled(block: dict[str, Any]) -> dict[str, Any]:
        return {
            "note_crop": [
                0,
                _scale_point(block["_note_top"], height_scale),
                original_width,
                _scale_point(block["_note_bottom"], height_scale),
            ],
            "lyric_rows": [
                [
                    _scale_point(row[0], height_scale),
                    _scale_point(row[1], height_scale),
                ]
                for row in block["_rows"]
            ],
            "tail_crops": [
                [
                    0,
                    _scale_point(box[1], height_scale),
                    original_width,
                    _scale_point(box[3], height_scale),
                ]
                for box in block["_tail"]
            ],
        }

    from .auto_layout import (
        _positioned_page_label,
        _safe_stem,
        _split_title,
    )

    stem = _safe_stem(source_path)
    detected_number, detected_title = _split_title(stem)
    number = (song_number or detected_number).strip()
    title = (song_title or detected_title or stem).strip()
    prefix = f"{number}-{title}" if number else title
    header_box = [
        0,
        0,
        original_width,
        _scale_point(header_bottom, height_scale),
    ]

    config: dict[str, Any] = {
        "base_dir": str(source_path.parent),
        "source": str(source_path),
        "output_dir": str(source_path.parent / "outputs" / prefix),
        "song": {"number": number, "title": title, "file_prefix": prefix},
        "header_crop": header_box,
        "page": {
            "width": original_width,
            "background": [255, 255, 255],
            "bottom_margin": 50,
        },
        "page_label": _positioned_page_label(
            image,
            original_width,
            header_box[3],
        ),
        "verse_labels": [f"第{index + 1}段" for index in range(verse_count)],
        "bold_mode": "none",
        "bold_strength": 0,
        "systems": [scaled(block) for block in verse_blocks],
        "options": {
            "include_chorus_on_verse_pages": False,
            "make_chorus_page": bool(chorus_blocks),
        },
        "_auto_layout": True,
        "_staff_layout": True,
    }
    if chorus_blocks:
        config["chorus"] = {
            "label": "副歌",
            "blocks": [scaled(block) for block in chorus_blocks],
        }
    return config
