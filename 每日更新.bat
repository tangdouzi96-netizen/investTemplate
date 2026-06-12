@echo off
chcp 65001 >nul

echo.
echo ==========================================
echo     持仓追踪看板 - 每日更新
echo     日期：%date% %time:~0,8%
echo ==========================================
echo.

:: ── 运行数据更新脚本 ─────────────────────────────────────
echo [1/2] 正在获取最新行情数据...
echo   数据来源：akshare（A股）+ yfinance（港股）交叉验证
echo   请耐心等待，大约需要 10-30 秒...
echo.

python scripts/update_position_tracker.py

if %errorlevel% neq 0 (
    echo.
    echo ==========================================
    echo   [警告] 数据更新未完全成功
    echo ==========================================
    echo.
    echo 可能原因：
    echo   1. 网络连接异常（a股/港股数据源暂时不可用）
    echo   2. Excel 文件被占用（请关闭 Excel 后重试）
    echo   3. 部分数据源超时（可稍后重试）
    echo.
    pause
    exit /b 1
)

echo.
echo   行情数据已更新。
echo.

:: ── 构建看板 ─────────────────────────────────────────────
echo [2/2] 正在构建看板页面...
npx vitepress build

if %errorlevel% neq 0 (
    echo [警告] 页面构建失败，但数据可能已更新。
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   更新完成！
echo ==========================================
echo.
echo 数据已刷新，请运行「查看看板.bat」在浏览器中查看。
echo.

pause
