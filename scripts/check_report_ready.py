#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告就绪门禁校验脚本 (V5.5.14 数据溯源硬门禁)

在生成/更新投资分析报告"写作阶段"前必须运行并通过。
校验数据溯源表是否满足进入报告写作的硬条件。

使用方法：
    python scripts/check_report_ready.py 601225
    python scripts/check_report_ready.py 数据溯源/陕西煤业_601225_数据溯源表.md

返回码：
    0 - 通过，可进入报告写作
    1 - 失败，禁止写报告（缺溯源表/有未解决🔴/A区缺页码）
    2 - 通过但有警告（存在⚠️待验证项），建议复核
"""

import sys
import re
from pathlib import Path

# Windows 控制台默认 GBK，强制 UTF-8 避免 emoji/中文报错
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 核心数据科目关键词：A 区必须能定位到这些项并带页码
CORE_KEYWORDS = [
    "货币资金", "现金",
    "营业收入",
    "归母净利润", "净利润",
    "经营活动产生的现金流量净额", "经营现金流", "经营活动现金流",
    "借款", "有息负债",
    "购建", "固定资产",
    "股本",
]

# 编号格式：A01 / B01 / A-PL 等数据行
ROW_NO_RE = re.compile(r"^[A-Z]\d{1,3}$")
PAGE_RE = re.compile(r"[pP]\d+")


def find_table(code_or_path: str) -> Path | None:
    p = Path(code_or_path)
    if p.suffix == ".md" and p.exists():
        return p
    base = Path("数据溯源")
    if not base.exists():
        return None
    candidates = [
        f for f in base.glob(f"*{code_or_path}*数据溯源表.md")
        if "_org" not in f.name
    ]
    return candidates[0] if candidates else None


def parse_rows(text: str):
    """返回数据行列表：[(编号, 科目, 整行文本)]"""
    rows = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        no = cells[0]
        if ROW_NO_RE.match(no):
            subject = cells[1]
            rows.append((no, subject, line))
    return rows


def main() -> int:
    if len(sys.argv) < 2:
        print("[USAGE] python scripts/check_report_ready.py <股票代码|溯源表路径>")
        return 1

    table = find_table(sys.argv[1])
    print("=" * 60)
    print("[CHECK] 报告就绪门禁校验")
    print("=" * 60)

    if table is None or not table.exists():
        print(f"[FAIL] 未找到数据溯源表：{sys.argv[1]}")
        print("       报告写作前必须先生成 数据溯源/{公司}_{代码}_数据溯源表.md")
        return 1

    print(f"[OK]   溯源表：{table}")
    text = table.read_text(encoding="utf-8")
    rows = parse_rows(text)
    if not rows:
        print("[FAIL] 溯源表中未解析到任何数据行（编号如 A01），格式异常")
        return 1
    print(f"[OK]   解析到 {len(rows)} 条数据行")

    errors, warnings = [], []

    # 1. 未解决 🔴
    red_rows = [(no, subj) for no, subj, line in rows if "🔴" in line]
    if red_rows:
        for no, subj in red_rows:
            errors.append(f"未解决🔴：{no} {subj}（差值≥5%，必须核实修正）")

    # 2. ⚠️ 待验证
    warn_rows = [(no, subj) for no, subj, line in rows if "⚠️" in line]
    for no, subj in warn_rows:
        warnings.append(f"待验证⚠️：{no} {subj}")

    # 3. A 区核心科目必须带页码
    a_rows = [(no, subj, line) for no, subj, line in rows if no.startswith("A")]
    for no, subj, line in a_rows:
        if "➖" in line:
            continue
        hit_core = any(kw in subj for kw in CORE_KEYWORDS)
        if hit_core and not PAGE_RE.search(line):
            errors.append(f"核心科目缺页码：{no} {subj}（A区必须标注 p+页码）")

    # 汇总
    print("-" * 60)
    if errors:
        print(f"[FAIL] 发现 {len(errors)} 个阻断性问题：")
        for e in errors:
            print(f"   [X] {e}")
    if warnings:
        print(f"[WARN] 发现 {len(warnings)} 个待复核项：")
        for w in warnings:
            print(f"   [!] {w}")

    print("-" * 60)
    if errors:
        print("[RESULT] 不通过，禁止进入报告写作。请先修正溯源表。")
        return 1
    if warnings:
        print("[RESULT] 通过但有警告，建议复核⚠️项后再写报告。")
        return 2
    print("[RESULT] 通过，可进入报告写作。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
