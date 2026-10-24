from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .service import current_version


DEFAULT_UPDATE_URL = (
    "https://api.github.com/repos/WangYufan/"
    "grace-hymn-splitter/releases/latest"
)


def _version_tuple(value: str) -> tuple[int, ...]:
    numbers = []
    for part in str(value or "").lstrip("v").split("."):
        digits = "".join(character for character in part if character.isdigit())
        numbers.append(int(digits or 0))
    return tuple(numbers)


def _update_url() -> str:
    configured = os.environ.get("HYMN_SPLITTER_UPDATE_URL", "").strip()
    if configured:
        return configured
    config_path = Path(__file__).resolve().parent.parent / "app_config.json"
    if config_path.is_file():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            configured = str(data.get("update_url", "")).strip()
        except Exception:
            configured = ""
    return configured or DEFAULT_UPDATE_URL


def check_for_updates(timeout: int = 6) -> dict[str, Any]:
    current = current_version()
    url = _update_url()
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "grace-hymn-splitter-update-check",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return {
                "ok": False,
                "current": current,
                "error": "暂未找到公开更新源。发布到 GitHub Releases 后即可检查更新。",
                "release_url": url,
            }
        return {
            "ok": False,
            "current": current,
            "error": f"检查更新失败：HTTP {error.code}",
            "release_url": url,
        }
    except Exception as error:
        return {
            "ok": False,
            "current": current,
            "error": f"暂时无法连接更新服务：{error}",
            "release_url": url,
        }

    latest = str(payload.get("tag_name") or payload.get("name") or "").lstrip("v")
    release_url = str(payload.get("html_url") or "").strip()
    body = str(payload.get("body") or "").strip()
    if not latest:
        return {
            "ok": False,
            "current": current,
            "error": "更新源没有返回版本号。",
            "release_url": release_url or url,
        }
    return {
        "ok": True,
        "current": current,
        "latest": latest,
        "has_update": _version_tuple(latest) > _version_tuple(current),
        "release_url": release_url or url,
        "notes": body[:1200],
    }
