from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .auto_layout import AutoLayoutError, detect_layout
from .config import ConfigError, list_configs, load_config
from .imaging import build_pages
from .inspect import inspect_image


PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_DIR / "configs"
OUTPUT_DIR = PROJECT_DIR / "outputs"


def _build(config_path: Path, with_chorus: bool | None) -> int:
    config = load_config(config_path)
    outputs = build_pages(config, force_chorus=with_chorus)
    print(f"已生成 {len(outputs)} 张图片：")
    for output in outputs:
        print(f"  {output}")
    return 0


def _inspect(source: Path) -> int:
    outputs = inspect_image(source, OUTPUT_DIR / "_inspect")
    print("已生成坐标参考：")
    for output in outputs:
        print(f"  {output}")
    return 0


def _auto(source: Path, output: Path | None) -> int:
    config = detect_layout(source)
    if output is not None:
        output = output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"已写入自动识别配置：{output}")
    else:
        print(json.dumps(config, ensure_ascii=False, indent=2))
    return 0


def _interactive() -> int:
    configs = list_configs(CONFIG_DIR)
    if not configs:
        print(f"没有找到配置文件：{CONFIG_DIR}")
        return 1

    print("可用歌谱：")
    for index, config_path in enumerate(configs, start=1):
        config = load_config(config_path)
        print(
            f"  {index}. {config['song'].get('number', '')} "
            f"{config['song'].get('title', config_path.stem)}"
        )

    choice = input("请选择编号（直接回车选择 1）：").strip() or "1"
    try:
        config_path = configs[int(choice) - 1]
    except (ValueError, IndexError):
        print("编号无效。")
        return 1
    return _build(config_path, None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hymn-splitter",
        description="拆分歌谱、加粗歌词，并输出适合 PPT 的分段图片。",
    )
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build", help="按配置生成图片")
    build_parser.add_argument("config", type=Path, help="JSON 配置文件")
    chorus_group = build_parser.add_mutually_exclusive_group()
    chorus_group.add_argument(
        "--with-chorus",
        action="store_true",
        help="每段页面末尾附上副歌",
    )
    chorus_group.add_argument(
        "--without-chorus",
        action="store_true",
        help="每段页面不附副歌",
    )

    inspect_parser = subparsers.add_parser("inspect", help="生成换谱用的坐标参考图")
    inspect_parser.add_argument("source", type=Path, help="歌谱图片")

    auto_parser = subparsers.add_parser("auto", help="自动识别常见简谱版式")
    auto_parser.add_argument("source", type=Path, help="歌谱图片")
    auto_parser.add_argument(
        "--output",
        type=Path,
        help="把识别结果写成 JSON 配置文件",
    )

    subparsers.add_parser("list", help="列出可用配置")
    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            force_chorus = None
            if args.with_chorus:
                force_chorus = True
            elif args.without_chorus:
                force_chorus = False
            return _build(args.config.resolve(), force_chorus)
        if args.command == "inspect":
            return _inspect(args.source.resolve())
        if args.command == "auto":
            return _auto(args.source.resolve(), args.output)
        if args.command == "list":
            for config_path in list_configs(CONFIG_DIR):
                print(config_path)
            return 0
        return _interactive()
    except (AutoLayoutError, ConfigError, FileNotFoundError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
