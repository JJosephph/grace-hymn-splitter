from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "logo-options" / "logo-04-text-minimal.png"
SMALL_SOURCE = ROOT / "docs" / "logo-options" / "logo-open-book.png"
BRAND_DIR = ROOT / "assets" / "branding"
FRONTEND_ASSET_DIR = ROOT / "frontend" / "grace-hymn-splitter-ui" / "src" / "assets"


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Selected logo was not found: {SOURCE}")

    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_ASSET_DIR.mkdir(parents=True, exist_ok=True)

    image = Image.open(SOURCE).convert("RGBA")
    image.save(BRAND_DIR / "logo.png")
    image.save(
        BRAND_DIR / "logo.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    small = Image.open(SMALL_SOURCE).convert("RGBA")
    small.resize((55, 55), Image.Resampling.LANCZOS).save(BRAND_DIR / "logo-small.png")
    shutil.copyfile(BRAND_DIR / "logo.png", FRONTEND_ASSET_DIR / "logo.png")


if __name__ == "__main__":
    main()
