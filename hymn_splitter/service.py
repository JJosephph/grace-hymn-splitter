from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from . import __version__ as package_version
from .auto_layout import detect_layout
from .config import load_config
from .imaging import build_pages


PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_DIR / "configs"


def _runtime_app_dir() -> Path:
    """Return the writable product directory for source and frozen builds."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return PROJECT_DIR


APP_DIR = _runtime_app_dir()
DEFAULT_OUTPUT_DIR = APP_DIR / ("输出" if getattr(sys, "frozen", False) else "outputs")


def current_version() -> str:
    version_file = PROJECT_DIR / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip() or package_version
    return package_version


def _safe_name(value: str, fallback: str) -> str:
    value = re.sub(r'[\\/:*?"<>|]+', "-", str(value or "")).strip(" .-")
    return value or fallback


def _find_matching_config(source_path: Path) -> Path | None:
    """Use a hand-tuned config for the bundled sample images."""
    source_path = source_path.resolve()
    try:
        source_size = ImageOps.exif_transpose(Image.open(source_path)).size
    except Exception:
        source_size = None
    for config_path in sorted(CONFIG_DIR.glob("*.json")):
        try:
            config = load_config(config_path)
        except Exception:
            continue
        configured_source = Path(config["_source_path"]).resolve()
        if configured_source == source_path:
            return config_path
        if source_path.stem in {
            config_path.stem,
            str(config.get("song", {}).get("file_prefix", "")),
        }:
            if source_size is not None:
                try:
                    configured_size = Image.open(configured_source).size
                except Exception:
                    configured_size = None
                if configured_size is not None and configured_size != source_size:
                    continue
            return config_path
    return None


def prepare_layout(
    source_path: str | Path,
    *,
    output_root: str | Path | None = None,
    song_number: str = "",
    song_title: str = "",
) -> tuple[dict[str, Any], str]:
    """Prepare a layout config, preferring a known sample config.

    The automatic detector is used for new images. A matching bundled config
    wins so the corrected lyric replacements in the sample songs are kept.
    """
    source = Path(source_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"找不到歌谱图片：{source}")

    matched_config = _find_matching_config(source)
    if matched_config is not None:
        config = load_config(matched_config)
        config["_source_path"] = source
        mode = "known"
    else:
        config = detect_layout(
            source,
            song_number=song_number,
            song_title=song_title,
        )
        config["_source_path"] = source
        config["_verse_count"] = len(config["verse_labels"])
        mode = "auto"

    number = str(song_number or config.get("song", {}).get("number", "")).strip()
    title = str(song_title or config.get("song", {}).get("title", "")).strip()
    title = _safe_name(title, source.stem)
    prefix = f"{number}-{title}" if number else title
    config.setdefault("song", {})
    config["song"].update(
        {
            "number": number,
            "title": title,
            "file_prefix": prefix,
        }
    )

    output_root_path = Path(output_root).expanduser().resolve() if output_root else DEFAULT_OUTPUT_DIR
    output_dir = output_root_path / prefix
    config["output_dir"] = str(output_dir)
    config["_output_dir"] = output_dir
    config["base_dir"] = str(source.parent)
    config["header_strategy"] = config.get(
        "header_strategy",
        "full_first_page_then_compact",
    )
    config["compact_header_height"] = int(
        config.get(
            "compact_header_height",
            max(92, min(180, int(int(config["page"].get("width", 1600)) * 0.065))),
        )
    )
    return config, mode


def apply_build_options(
    config: dict[str, Any],
    *,
    bold_mode: str = "none",
    keep_metadata_first_page: bool = True,
    make_chorus_page: bool = True,
    line_spacing: str = "normal",
) -> dict[str, Any]:
    config["bold_mode"] = str(bold_mode or "none").strip().lower()
    config["bold_strength"] = {
        "none": 0,
        "light": 1,
        "strong": 2,
    }.get(config["bold_mode"], int(config.get("bold_strength", 0)))
    config["header_strategy"] = (
        "full_first_page_then_compact"
        if keep_metadata_first_page
        else "full"
    )
    config.setdefault("options", {})
    spacing_mode = str(line_spacing or "normal").strip().lower()
    if spacing_mode not in {"compact", "normal", "relaxed"}:
        spacing_mode = "normal"
    config["options"]["line_spacing"] = spacing_mode
    config["options"]["make_chorus_page"] = bool(
        make_chorus_page and bool(config.get("chorus"))
    )
    config["options"]["include_chorus_on_verse_pages"] = bool(
        config["options"].get("include_chorus_on_verse_pages", False)
    )
    return config


def build_from_source(
    source_path: str | Path,
    *,
    output_root: str | Path | None = None,
    song_number: str = "",
    song_title: str = "",
    bold_mode: str = "none",
    keep_metadata_first_page: bool = True,
    make_chorus_page: bool = True,
    line_spacing: str = "normal",
) -> dict[str, Any]:
    config, layout_mode = prepare_layout(
        source_path,
        output_root=output_root,
        song_number=song_number,
        song_title=song_title,
    )
    apply_build_options(
        config,
        bold_mode=bold_mode,
        keep_metadata_first_page=keep_metadata_first_page,
        make_chorus_page=make_chorus_page,
        line_spacing=line_spacing,
    )

    output_dir = Path(config["_output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = config["song"]["file_prefix"]
    # Regeneration is intentionally idempotent: the same song replaces its
    # previous PNGs instead of accumulating confusing old pages.
    for old_file in output_dir.glob(f"{prefix}-*.png"):
        old_file.unlink(missing_ok=True)

    outputs = build_pages(config)
    return {
        "ok": True,
        "layout_mode": layout_mode,
        "config": config,
        "output_dir": str(output_dir),
        "outputs": [str(path) for path in outputs],
        "count": len(outputs),
    }
