from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a hymn layout config is invalid."""


def _require(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise ConfigError(f"{context} is missing required key: {key}")
    return mapping[key]


def _resolve(base_dir: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _validate_box(box: list[int], context: str) -> None:
    if len(box) != 4:
        raise ConfigError(f"{context} must contain [left, top, right, bottom]")
    left, top, right, bottom = box
    if right <= left or bottom <= top:
        raise ConfigError(f"{context} has invalid bounds: {box}")


def _validate_lyric_row(row: list[int], context: str) -> None:
    if len(row) == 2:
        top, bottom = row
        if bottom <= top:
            raise ConfigError(f"{context} has invalid bounds: {row}")
        return
    _validate_box(row, context)


def _validate_range(value: list[int], context: str) -> None:
    if len(value) != 2:
        raise ConfigError(f"{context} must contain [start, end]")
    start, end = value
    if end <= start:
        raise ConfigError(f"{context} has invalid range: {value}")


def load_config(config_path: str | Path) -> dict[str, Any]:
    config_path = Path(config_path).resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    base_dir = _resolve(config_path.parent, config.get("base_dir", "."))
    source = _resolve(base_dir, _require(config, "source", "config"))
    output_dir = _resolve(base_dir, _require(config, "output_dir", "config"))

    config["_config_path"] = config_path
    config["_base_dir"] = base_dir
    config["_source_path"] = source
    config["_output_dir"] = output_dir

    if not source.exists():
        raise ConfigError(f"source image does not exist: {source}")

    page = _require(config, "page", "config")
    page.setdefault("background", [255, 255, 255])
    page.setdefault("bottom_margin", 60)

    header_crop = _require(config, "header_crop", "config")
    _validate_box(header_crop, "header_crop")

    systems = _require(config, "systems", "config")
    if not systems:
        raise ConfigError("systems must contain at least one system")

    verse_labels = config.get("verse_labels")
    if verse_labels is not None:
        verse_count = len(verse_labels)
    elif "verse_count" in config:
        verse_count = int(config["verse_count"])
    else:
        verse_count = min(len(system.get("lyric_rows", [])) for system in systems)
    if verse_count < 1:
        raise ConfigError("verse_count must be at least 1")
    config["_verse_count"] = verse_count

    for index, system in enumerate(systems, start=1):
        _validate_box(
            _require(system, "note_crop", f"systems[{index}]"),
            f"systems[{index}].note_crop",
        )
        lyric_rows = _require(system, "lyric_rows", f"systems[{index}]")
        if len(lyric_rows) < verse_count:
            raise ConfigError(
                f"systems[{index}].lyric_rows must contain at least {verse_count} rows"
            )
        for row_index, row in enumerate(lyric_rows, start=1):
            _validate_lyric_row(row, f"systems[{index}].lyric_rows[{row_index}]")

        replacement = system.get("replace")
        if replacement is None:
            continue
        _validate_range(
            _require(replacement, "text_area", f"systems[{index}].replace"),
            f"systems[{index}].replace.text_area",
        )
        verses = _require(
            replacement, "verses", f"systems[{index}].replace"
        )
        if len(verses) < verse_count:
            raise ConfigError(
                f"systems[{index}].replace.verses must contain at least "
                f"{verse_count} verses"
            )
        x_centers = _require(
            replacement, "x_centers", f"systems[{index}].replace"
        )
        if len(x_centers) != 11:
            raise ConfigError(
                f"systems[{index}].replace.x_centers must contain 11 positions"
            )
        for verse_index, verse in enumerate(verses, start=1):
            if "parts" not in verse or len(verse["parts"]) != 2:
                raise ConfigError(
                    f"systems[{index}].replace.verses[{verse_index}] "
                    "must contain two lyric parts"
                )

    chorus = config.get("chorus")
    if chorus:
        blocks = _require(chorus, "blocks", "chorus")
        if not blocks:
            raise ConfigError("chorus.blocks must not be empty")
        for index, block in enumerate(blocks, start=1):
            _validate_box(
                _require(block, "note_crop", f"chorus.blocks[{index}]"),
                f"chorus.blocks[{index}].note_crop",
            )
            lyric_rows = block.get("lyric_rows")
            if lyric_rows is not None:
                if not lyric_rows:
                    raise ConfigError(
                        f"chorus.blocks[{index}].lyric_rows must not be empty"
                    )
                for row_index, row in enumerate(lyric_rows, start=1):
                    _validate_lyric_row(
                        row,
                        f"chorus.blocks[{index}].lyric_rows[{row_index}]",
                    )
            else:
                _validate_lyric_row(
                    _require(block, "lyric_row", f"chorus.blocks[{index}]"),
                    f"chorus.blocks[{index}].lyric_row",
                )

    return config


def list_configs(configs_dir: Path) -> list[Path]:
    return sorted(configs_dir.glob("*.json"))
