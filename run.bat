@echo off
chcp 65001 >nul
cd /d "%~dp0"

py -c "import PIL, webview" >nul 2>nul
if errorlevel 1 (
  echo 正在安装运行依赖...
  py -m pip install -r requirements.txt
  if errorlevel 1 (
    echo 依赖安装失败，请检查网络或 Python 环境。
    pause
    exit /b 1
  )
)

py run.py
if errorlevel 1 pause
