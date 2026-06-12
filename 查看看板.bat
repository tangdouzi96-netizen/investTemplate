@echo off
chcp 65001 >nul

echo.
echo ==========================================
echo     持仓追踪看板
echo ==========================================
echo.
echo 正在启动本地服务器...
echo 浏览器将自动打开 http://localhost:5173/持仓追踪/
echo 按 Ctrl+C 可停止服务器。
echo.

npx vitepress dev
