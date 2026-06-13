#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网页索引同步校验脚本

校验 07-分析输出/ 下的投资分析报告，是否已同步登记到三处网页索引：
  1. 07-分析输出/index.md   （目录页）
  2. index.md               （首页"最新分析报告"）
  3. .vitepress/config.mjs  （侧边栏）

使用方法：
    python scripts/check_index_sync.py

返回码：
    0 - 三处索引均已同步
    1 - 存在缺失，打印缺失清单
"""

import sys
from pathlib import Path

# Windows 控制台默认 GBK，强制 UTF-8 避免 emoji/中文报错
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPORT_DIR = Path("07-分析输出")
INDEX_DIR_PAGE = REPORT_DIR / "index.md"
HOME_PAGE = Path("index.md")
SIDEBAR = Path(".vitepress/config.mjs")


def main() -> int:
    print("=" * 60)
    print("[CHECK] 网页索引同步校验")
    print("=" * 60)

    if not REPORT_DIR.exists():
        print(f"[FAIL] 目录不存在：{REPORT_DIR}")
        return 1

    reports = sorted(REPORT_DIR.glob("*_投资分析报告.md"))
    if not reports:
        print("[OK]   无投资分析报告，跳过。")
        return 0

    texts = {}
    for f in (INDEX_DIR_PAGE, HOME_PAGE, SIDEBAR):
        texts[f] = f.read_text(encoding="utf-8") if f.exists() else None
        if texts[f] is None:
            print(f"[WARN] 索引文件不存在：{f}")

    missing = {}
    for report in reports:
        stem = report.stem  # 如 泡泡玛特_09992_投资分析报告
        miss_in = []
        for f in (INDEX_DIR_PAGE, HOME_PAGE, SIDEBAR):
            txt = texts[f]
            if txt is None:
                miss_in.append(f.name)
                continue
            if stem not in txt:
                miss_in.append(f.name)
        if miss_in:
            missing[stem] = miss_in

    print(f"[INFO] 共 {len(reports)} 份报告")
    print("-" * 60)
    if not missing:
        print("[RESULT] 通过，三处索引均已同步。")
        return 0

    print(f"[FAIL] {len(missing)} 份报告索引缺失：")
    for stem, miss_in in missing.items():
        print(f"   [X] {stem}")
        print(f"      缺失于：{', '.join(miss_in)}")
    print("-" * 60)
    print("[RESULT] 不通过，请补齐上述索引后重跑。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
