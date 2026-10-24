from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from .desktop_api import DesktopApi


def _schedule_process_exit() -> None:
    """Ensure the WebView2 process tree is not left behind after closing."""

    def exit_after_close() -> None:
        time.sleep(0.8)
        os._exit(0)

    threading.Thread(target=exit_after_close, daemon=True).start()


def main() -> None:
    try:
        import webview
    except ImportError as error:
        raise SystemExit(
            "缺少桌面界面依赖 pywebview。请先运行：py -m pip install -r requirements.txt"
        ) from error

    api = DesktopApi()
    html_file = Path(__file__).resolve().parent / "web" / "index.html"
    if not html_file.is_file():
        raise FileNotFoundError(f"界面文件不存在：{html_file}")

    window = webview.create_window(
        "恩典歌谱转换PPT大图",
        url=str(html_file),
        js_api=api,
        width=1320,
        height=880,
        min_size=(1040, 700),
        resizable=True,
        background_color="#fbfbfd",
        text_select=True,
    )
    api.attach_window(window)
    window.events.closing += _schedule_process_exit
    window.events.closed += _schedule_process_exit
    try:
        webview.start(
            gui="edgechromium",
            debug=False,
            private_mode=False,
            storage_path=str(
                Path.home() / "AppData" / "Local" / "GraceHymnSplitter" / "webview"
            ),
        )
    except Exception:
        # Older Windows installations may not have Edge WebView2 available.
        # pywebview can still use its default GUI backend in that case.
        webview.start(
            debug=False,
            private_mode=False,
            storage_path=str(
                Path.home() / "AppData" / "Local" / "GraceHymnSplitter" / "webview"
            ),
        )
