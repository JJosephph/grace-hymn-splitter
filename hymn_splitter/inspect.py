from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _ink_runs(gray: Image.Image, threshold: int = 100) -> list[tuple[int, int]]:
    counts: list[tuple[int, int]] = []
    for y in range(gray.height):
        count = sum(1 for x in range(80, gray.width - 80) if gray.getpixel((x, y)) < threshold)
        counts.append((y, count))

    runs: list[tuple[int, int]] = []
    start: int | None = None
    last = 0
    for y, count in counts:
        if count > 15:
            if start is None:
                start = y
            last = y
        elif start is not None and y - last > 5:
            runs.append((start, last))
            start = None
    if start is not None:
        runs.append((start, last))
    return runs


def inspect_image(source_path: str | Path, output_dir: str | Path) -> list[Path]:
    source_path = Path(source_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    image = Image.open(source_path).convert("RGB")
    gray = image.convert("L")
    runs = _ink_runs(gray)

    report = output_dir / f"{source_path.stem}-投影报告.txt"
    report.write_text(
        "\n".join(f"{start:4d} - {end:4d}  height={end - start + 1}" for start, end in runs),
        encoding="utf-8",
    )

    guide = image.copy()
    draw = ImageDraw.Draw(guide)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 18)
    for y in range(0, image.height, 100):
        draw.line((0, y, image.width, y), fill=(220, 40, 40), width=1)
        draw.text((8, y + 3), str(y), font=font, fill=(180, 0, 0))
    for start, end in runs:
        draw.line((0, start, image.width, start), fill=(40, 100, 220), width=1)
        draw.line((0, end, image.width, end), fill=(40, 100, 220), width=1)

    guide_path = output_dir / f"{source_path.stem}-坐标参考.png"
    guide.save(guide_path, format="PNG", optimize=True)
    return [report, guide_path]
