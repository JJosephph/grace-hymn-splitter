# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)


project_dir = Path(SPECPATH).resolve()

datas = [
    (str(project_dir / "VERSION"), "."),
    (str(project_dir / "app_config.json"), "."),
    (str(project_dir / "configs"), "configs"),
    (str(project_dir / "hymn_splitter" / "web"), "hymn_splitter/web"),
]
datas += collect_data_files("webview")

binaries = collect_dynamic_libs("webview")

hiddenimports = [
    "clr_loader",
    "pythonnet",
    "webview.platforms.edgechromium",
    "webview.platforms.mshtml",
    "webview.platforms.win32",
    "webview.platforms.winforms",
]
hiddenimports += collect_submodules("webview")

a = Analysis(
    ["run.py"],
    pathex=[str(project_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GraceHymnSplitter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
