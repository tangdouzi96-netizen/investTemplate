@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo     持仓追踪看板 - 环境安装
echo ==========================================
echo.

:: ── 检查 Python ──────────────────────────────────────────
echo [1/4] 检查 Python 环境...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8 或更高版本。
    echo 下载地址：https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH"。
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
for /f "tokens=2 delims=." %%a in ("!PY_VER!") do set PY_MINOR=%%a
echo   Python 版本：!PY_VER!

if !PY_MINOR! lss 8 (
    echo [错误] Python 版本过低（当前 !PY_VER!），需要 3.8 或更高版本。
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)
echo   Python 检查通过。
echo.

:: ── 检查 Node.js ─────────────────────────────────────────
echo [2/4] 检查 Node.js 环境...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js 18 或更高版本。
    echo 下载地址：https://nodejs.org/
    echo 安装 LTS 版本即可。
    echo.
    pause
    exit /b 1
)

for /f "tokens=1 delims=v" %%v in ('node --version 2^>^&1') do (
    set NODE_VER_FULL=%%v
    for /f "tokens=1 delims=." %%m in ("!NODE_VER_FULL!") do set NODE_MAJOR=%%m
)
echo   Node.js 版本：v!NODE_VER_FULL!

if !NODE_MAJOR! lss 18 (
    echo [错误] Node.js 版本过低（当前 v!NODE_VER_FULL!），需要 18 或更高版本。
    echo 下载地址：https://nodejs.org/
    pause
    exit /b 1
)
echo   Node.js 检查通过。
echo.

:: ── 安装 Python 依赖 ─────────────────────────────────────
echo [3/4] 安装 Python 依赖（akshare yfinance openpyxl）...
pip install akshare yfinance openpyxl -q
if %errorlevel% neq 0 (
    echo [警告] Python 依赖安装失败，请手动执行：
    echo   pip install akshare yfinance openpyxl
) else (
    echo   Python 依赖安装完成。
)
echo.

:: ── 安装 Node 依赖 ───────────────────────────────────────
echo [4/4] 安装 Node.js 依赖（VitePress）...
if not exist "node_modules\" (
    call npm install
    if %errorlevel% neq 0 (
        echo [警告] npm install 失败，请手动执行：npm install
    ) else (
        echo   Node.js 依赖安装完成。
    )
) else (
    echo   node_modules 已存在，跳过安装。
    echo   如需重新安装，请先删除 node_modules 文件夹再运行本脚本。
)
echo.

:: ── 完成 ─────────────────────────────────────────────────
echo ==========================================
echo   安装完成！
echo ==========================================
echo.
echo 使用方法：
echo   每日更新.bat  ——  获取最新行情数据
echo   查看看板.bat  ——  启动网页看板
echo.
echo 首次使用请先运行「每日更新.bat」获取数据，
echo 然后再运行「查看看板.bat」在浏览器中查看。
echo.

pause
