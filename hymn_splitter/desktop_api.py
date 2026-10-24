from __future__ import annotations

import json
import os
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

from .service import (
    DEFAULT_OUTPUT_DIR,
    PROJECT_DIR,
    build_from_source,
    current_version,
)
from .update import check_for_updates


def _file_uri(path: str | Path) -> str:
    return Path(path).resolve().as_uri()


class DesktopApi:
    """Small js_api surface used by the pywebview window."""

    def __init__(self) -> None:
        self._window: Any = None
        self._lock = threading.RLock()
        self._job: dict[str, Any] = {
            "status": "idle",
            "message": "等待制作",
            "progress": 0,
            "logs": [],
            "result": {},
            "error": "",
        }

    def attach_window(self, window: Any) -> None:
        self._window = window

    # ---------- bootstrap and dialogs ----------
    def get_bootstrap(self) -> dict[str, Any]:
        settings = self._load_settings()
        return {
            "ok": True,
            "version": current_version(),
            "default_output_root": str(
                Path(settings.get("output_root") or DEFAULT_OUTPUT_DIR).resolve()
            ),
            "settings": settings,
            "project_dir": str(PROJECT_DIR),
            "brand": {
                "name": "恩典歌谱转换PPT大图",
                "subtitle": "恩典简谱分段转换",
                "tagline": "让每一段诗歌，在屏幕上清清楚楚。",
                "developer": "WangYufan",
                "license": "恩典开源免费软件",
            },
        }

    def choose_image(self) -> dict[str, Any]:
        try:
            path = self._dialog(
                "open",
                allow_multiple=False,
                file_types=(
                    "歌谱图片 (*.png;*.jpg;*.jpeg;*.webp;*.bmp)",
                    "所有文件 (*.*)",
                ),
            )
            name = Path(path).name if path else ""
            return {
                "ok": True,
                "path": path or "",
                "url": _file_uri(path) if path else "",
                "name": name,
            }
        except Exception as error:
            return {"ok": False, "error": str(error)}

    def choose_output_dir(self) -> dict[str, Any]:
        try:
            path = self._dialog("folder")
            return {"ok": True, "path": path or ""}
        except Exception as error:
            return {"ok": False, "error": str(error)}

    def on_drop(self, event: Any) -> dict[str, Any]:
        try:
            files = ((event or {}).get("dataTransfer") or {}).get("files") or []
            if not files:
                return {"ok": False, "error": "没有读取到拖入的图片。"}
            path = self._resolve_drop_path(files[0])
            if path is None:
                return {"ok": False, "error": "无法读取拖入图片的路径。"}
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                return {"ok": False, "error": "请拖入 PNG、JPG、JPEG、WEBP 或 BMP 歌谱图片。"}
            return {
                "ok": True,
                "path": str(path),
                "url": _file_uri(path),
                "name": path.name,
            }
        except Exception as error:
            return {"ok": False, "error": str(error)}

    # ---------- build ----------
    def start_build(
        self,
        source_path: str,
        song_number: str = "",
        song_title: str = "",
        output_root: str = "",
        bold_mode: str = "none",
        keep_metadata_first_page: bool = True,
        make_chorus_page: bool = True,
    ) -> dict[str, Any]:
        with self._lock:
            if self._job.get("status") == "running":
                return {"ok": False, "error": "正在制作，请稍等片刻。"}
            self._job = {
                "status": "running",
                "message": "正在读取歌谱…",
                "progress": 8,
                "logs": [
                    self._log_line("准备开始", "读取图片和页面结构"),
                ],
                "result": {},
                "error": "",
            }
        worker = threading.Thread(
            target=self._run_build,
            args=(
                source_path,
                song_number,
                song_title,
                output_root,
                bold_mode,
                bool(keep_metadata_first_page),
                bool(make_chorus_page),
            ),
            daemon=True,
        )
        worker.start()
        return {"ok": True}

    def _run_build(
        self,
        source_path: str,
        song_number: str,
        song_title: str,
        output_root: str,
        bold_mode: str,
        keep_metadata_first_page: bool,
        make_chorus_page: bool,
    ) -> None:
        try:
            self._set_job(message="正在识别乐谱行…", progress=28)
            result = build_from_source(
                source_path,
                output_root=output_root or None,
                song_number=song_number,
                song_title=song_title,
                bold_mode=bold_mode,
                keep_metadata_first_page=keep_metadata_first_page,
                make_chorus_page=make_chorus_page,
            )
            previews = [
                {
                    "name": Path(path).name,
                    "path": path,
                    "url": _file_uri(path),
                }
                for path in result.get("outputs", [])
            ]
            public_result = {
                key: value
                for key, value in result.items()
                if key not in {"config"}
            }
            public_result["previews"] = previews
            self._append_log(
                "生成完成",
                f"共生成 {public_result.get('count', len(previews))} 张分段大图",
            )
            self._set_job(
                status="completed",
                message=f"制作完成，共 {public_result.get('count', len(previews))} 张图。",
                progress=100,
                result=public_result,
            )
            saved_output_root = output_root or str(Path(public_result["output_dir"]).parent)
            self._save_settings(
                {
                    "output_root": saved_output_root,
                    "bold_mode": bold_mode,
                    "keep_metadata_first_page": keep_metadata_first_page,
                    "make_chorus_page": make_chorus_page,
                }
            )
        except Exception as error:
            message = str(error)
            self._append_log("出错了", message)
            self._set_job(
                status="failed",
                message="制作没有完成。",
                progress=100,
                error=message,
            )

    def get_job_state(self) -> dict[str, Any]:
        with self._lock:
            return {"ok": True, "job": dict(self._job)}

    # ---------- external actions ----------
    def open_path(self, path: str) -> dict[str, Any]:
        try:
            target = Path(path).resolve()
            if not target.exists():
                return {"ok": False, "error": "文件或目录不存在。"}
            os.startfile(str(target))
            return {"ok": True}
        except Exception as error:
            return {"ok": False, "error": str(error)}

    def open_url(self, url: str) -> dict[str, Any]:
        try:
            if not (url or "").strip():
                return {"ok": False, "error": "链接为空。"}
            webbrowser.open(url)
            return {"ok": True}
        except Exception as error:
            return {"ok": False, "error": str(error)}

    def check_updates(self) -> dict[str, Any]:
        return check_for_updates()

    def save_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        try:
            self._save_settings(values or {})
            return {"ok": True, "settings": self._load_settings()}
        except Exception as error:
            return {"ok": False, "error": str(error)}

    # ---------- internals ----------
    def _dialog(self, dialog_type: str, **kwargs: Any) -> str:
        if self._window is None:
            return ""
        if dialog_type == "folder":
            result = self._window.create_file_dialog(20)
        else:
            result = self._window.create_file_dialog(10, **kwargs)
        if not result:
            return ""
        if isinstance(result, (list, tuple)):
            return str(result[0])
        return str(result)

    @staticmethod
    def _resolve_drop_path(file_info: Any) -> Path | None:
        if isinstance(file_info, str):
            candidate = Path(file_info)
            return candidate.resolve() if candidate.is_file() else None
        raw_path = str(
            (file_info or {}).get("pywebviewFullPath")
            or (file_info or {}).get("path")
            or (file_info or {}).get("name")
            or ""
        ).strip()
        if not raw_path:
            return None
        candidate = Path(raw_path)
        if candidate.is_file():
            return candidate.resolve()
        expected_name = candidate.name
        try:
            from webview.dom import _dnd_state

            deadline = time.monotonic() + 1.5
            while time.monotonic() < deadline:
                for item in list(_dnd_state.get("paths", [])):
                    if not isinstance(item, (list, tuple)) or len(item) < 2:
                        continue
                    full_path = Path(str(item[1]))
                    if full_path.name != expected_name:
                        continue
                    _dnd_state["paths"].remove(item)
                    if full_path.is_file():
                        return full_path.resolve()
                time.sleep(0.05)
        except Exception:
            pass
        return None

    @staticmethod
    def _log_line(title: str, message: str) -> dict[str, str]:
        return {
            "time": time.strftime("%H:%M:%S"),
            "title": title,
            "message": message,
        }

    def _append_log(self, title: str, message: str) -> None:
        with self._lock:
            logs = list(self._job.get("logs", []))
            logs.append(self._log_line(title, message))
            self._job["logs"] = logs[-200:]

    def _set_job(self, **values: Any) -> None:
        with self._lock:
            self._job.update(values)

    @staticmethod
    def _settings_path() -> Path:
        base = Path(os.environ.get("APPDATA") or Path.home()) / "GraceHymnSplitter"
        return base / "settings.json"

    def _load_settings(self) -> dict[str, Any]:
        path = self._settings_path()
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_settings(self, values: dict[str, Any]) -> None:
        path = self._settings_path()
        current = self._load_settings()
        allowed = {
            "output_root",
            "bold_mode",
            "keep_metadata_first_page",
            "make_chorus_page",
        }
        for key, value in (values or {}).items():
            if key in allowed:
                current[key] = value
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
