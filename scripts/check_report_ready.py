#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告就绪门禁校验脚本 (V5.5.18 四层交叉校验 + WS 年份分层)

使用方法：
    python scripts/check_report_ready.py 601225
    python scripts/check_report_ready.py 数据溯源/陕西煤业_601225_数据溯源表.md

返回码：
    0 - 通过，可进入报告写作
    1 - 失败，禁止写报告
    2 - 通过但有警告（存在⚠️待验证项），建议复核
"""

import sys
import re
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

CORE_KEYWORDS = [
    "货币资金", "现金",
    "营业收入",
    "归母净利润", "净利润",
    "经营活动产生的现金流量净额", "经营现金流", "经营活动现金流",
    "借款", "有息负债",
    "购建", "固定资产",
    "股本",
]

# 每一行都须 WS 通过（在含 WS 列的表内）
CORE_WS_EACH_ROW = [
    "营业收入", "收益（营业收入）",
    "归母净利润", "归母溢利",
    "经营活动产生的现金流量净额", "经营活动现金流量净额",
    "经营活动现金流", "经营现金流", "经营业务现金",
    "购建固定资产",
    "每股股息", "每股股利", "股息总额", "派息合计",
    "分红总额",
    "有息负债合计",
]

# 组内至少一行 WS 通过即可（明细行允许 📝）
CORE_WS_GROUP_AT_LEAST_ONE: list[tuple[str, list[str]]] = [
    ("现金", ["货币资金", "现金及银行结余", "年末现金及现金等价物", "现金及银行"]),
    ("总负债", ["总负债", "负债合计"]),
    ("资产总计", ["资产总计", "资产总额"]),
]

MANDATORY_YEAR_GROUPS: list[tuple[str, list[str], bool]] = [
    ("营收", ["营业收入", "收益（营业收入）", "收益"], True),
    ("归母净利润", ["归母净利润", "归母溢利"], True),
    ("经营现金流", ["经营活动产生的现金流量净额", "经营现金流", "经营活动现金流"], True),
    ("CAPEX", ["购建固定资产", "购建", "CAPEX"], True),
    ("现金", ["货币资金", "现金及银行结余", "现金及现金等价物", "现金及银行"], True),
    ("总负债", ["总负债", "负债合计"], True),
    ("股本", ["股本", "总股本"], False),
]

WS_PASS_MARKS = ("✅", "🔗", "📄")
WS_FAIL_MARKS = ("📝", "⚠️")

FAB_KEYWORDS = ["websearch", "web search", "搜索结果", "联网搜索", "网络搜索", "百度", "谷歌", "google"]
CURRENCY_FLAG = ["港币", "港元", "hkd"]
MARKET_KEYWORDS = ["股价", "市值", "汇率", "52周", "成交", "收盘", "北向", "股东户数", "换手"]
CURRENCY_CORE_EXTRA = ["分红", "股息", "派息", "每股股利"]

REPORT_SECTIONS = [
    ("公司概览", ["公司概览", "公司简介", "业务概览"]),
    ("受限资金", ["受限", "使用受限", "所有权或使用权受到限制"]),
    ("两职合一", ["两职合一", "董事长兼", "董事长与总经理", "董事长、总经理"]),
]
BUY_SECTION_KEYWORDS = ["买入区间", "买点", "买入价", "目标买入"]
FORMULA_CHARS = ["=", "÷", "×", "/"]

MAX_WARN_ROWS = 3

ROW_NO_RE = re.compile(r"^[A-Z]\d{1,3}[a-z]?$")
PAGE_RE = re.compile(r"[pP]\d+")
YEAR_HEADER_RE = re.compile(r"202[1-5]")

EMPTY_LITERALS = frozenset({
    "", "—", "–", "-", "NA", "N/A", "n/a", "待查", "待补", "TBD", "...",
})

BS_RECON_RE = re.compile(
    r"BS\s*平衡|资产负债表.*平衡|资产[\d.]+\s*[=＝]\s*负债[\d.]+\s*\+\s*权益",
    re.I,
)
CF_RECON_RE = re.compile(
    r"CF\s*平衡|现金流量.*平衡|现金.*净增.*=.*经营",
    re.I,
)


def find_table(code_or_path: str) -> Path | None:
    p = Path(code_or_path)
    if p.suffix == ".md" and p.exists() and "数据溯源表" in p.name:
        return p
    base = Path("数据溯源")
    if not base.exists():
        return None
    candidates = [
        f for f in base.glob(f"*{code_or_path}*数据溯源表.md")
        if "_org" not in f.name
    ]
    return candidates[0] if candidates else None


def find_report(code_or_path: str) -> Path | None:
    p = Path(code_or_path)
    if p.suffix == ".md" and p.exists() and "投资分析报告" in p.name:
        return p
    base = Path("07-分析输出")
    if not base.exists():
        return None
    candidates = list(base.glob(f"*{code_or_path}*投资分析报告.md"))
    return candidates[0] if candidates else None


def is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return True
    return all(re.fullmatch(r":?-+:?", c.replace(" ", "")) for c in cells)


def is_placeholder(val: str) -> bool:
    v = val.strip()
    if v in EMPTY_LITERALS:
        return True
    if re.fullmatch(r"[-–—]+", v):
        return True
    if v.startswith("待") and ("查" in v or "补" in v):
        return True
    return False


def subject_matches(subject: str, keywords: list[str]) -> bool:
    for kw in keywords:
        if kw not in subject:
            continue
        if kw == "收益" and "投资" in subject:
            continue
        if kw == "现金" and "现金流" in subject:
            continue
        if kw == "净利润" and "归母" in subject:
            continue
        if kw == "年内溢利" and "归母" in subject:
            continue
        return True
    return False


def is_ws_excluded_subject(subject: str) -> bool:
    s = subject.replace("*", "").strip()
    return any(x in s for x in ("净增加", "受限", "流动负债", "非流动负债", "少数股东"))


def is_core_ws_each_row(subject: str) -> bool:
    if is_ws_excluded_subject(subject):
        return False
    return subject_matches(subject, CORE_WS_EACH_ROW)


def is_core_subject(subject: str) -> bool:
    return subject_matches(subject, CORE_KEYWORDS)


def is_derived_row(line: str) -> bool:
    return "➖" in line


def ws_passes(line: str) -> bool:
    if "🔴" in line:
        return False
    if any(m in line for m in WS_PASS_MARKS):
        return True
    if any(m in line for m in WS_FAIL_MARKS):
        return False
    return False


def year_from_header(header: str) -> str | None:
    m = YEAR_HEADER_RE.search(header)
    return m.group(0) if m else None


def parse_table_blocks(text: str) -> list[dict]:
    blocks = []
    current_header: list[str] | None = None
    current_rows: list[tuple[str, str, list[str], str]] = []

    def flush():
        nonlocal current_header, current_rows
        if current_header and current_rows:
            blocks.append({
                "header": current_header,
                "rows": current_rows,
                "has_ws": any(h.upper() == "WS" or h == "WS" for h in current_header),
            })
        current_header = None
        current_rows = []

    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            flush()
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if is_separator_row(cells):
            continue
        if cells and cells[0] in ("编号", "No"):
            flush()
            current_header = cells
            continue
        no = cells[0] if cells else ""
        if ROW_NO_RE.match(no) and no.startswith("A"):
            subject = cells[1] if len(cells) > 1 else ""
            current_rows.append((no, subject, cells, line))

    flush()
    return blocks


def year_columns(header: list[str]) -> list[tuple[int, str]]:
    cols = []
    for i, h in enumerate(header):
        y = year_from_header(h)
        if y:
            cols.append((i, y))
    return cols


def check_header_contract(text: str, errors: list):
    """表头契约：表头元信息须声明主币种与主单位。"""
    zone = text[:3000]
    has_currency = any(
        k in zone for k in ("币种", "主币种", "人民币", "港币", "港元", "RMB", "HKD")
    )
    has_unit = any(
        k in zone for k in ("单位", "主单位", "亿元", "万元", "百万", "千元")
    )
    if not has_currency:
        errors.append("表头契约：缺「币种」声明（表头元信息须写明主币种，禁止跨币混比）")
    if not has_unit:
        errors.append("表头契约：缺「单位」声明（表头元信息须写明主单位及 PDF→表内换算）")


def check_reconciliation(text: str, errors: list):
    """勾稽阻断：须有 BS/CF 平衡验算且标记通过（✅）。"""
    if not re.search(r"平衡验算|溯源表完成标准自检|自检块", text, re.I):
        errors.append("勾稽阻断：缺「平衡验算」或「溯源表完成标准自检」区块")
        return

    def block_passed(pattern: re.Pattern) -> bool:
        for line in text.splitlines():
            if not pattern.search(line):
                continue
            if "✅" in line and "❌" not in line:
                return True
        return False

    bs_ok = block_passed(BS_RECON_RE) or re.search(
        r"资产[\d.]+\s*[=＝]\s*[\d.]*\s*负债[\d.]+\s*\+\s*[\d.]*\s*权益.*✅",
        text,
        re.I,
    )
    cf_ok = block_passed(CF_RECON_RE)

    if not bs_ok:
        errors.append(
            "勾稽阻断：缺 BS 平衡验算通过（自检块须含「BS 平衡…✅」或 资产=负债+权益 ✅）"
        )
    if not cf_ok:
        errors.append(
            "勾稽阻断：缺 CF 平衡验算通过（自检块须含「CF 平衡…✅」或经营+投资+筹资勾稽 ✅）"
        )


def check_core_ws_validation(blocks: list[dict], errors: list, summary_tier_ok: bool = False):
    """核心行 WS：摘要科目逐行 ✅；验证汇总年份分层通过时主表可 📝。"""
    for block in blocks:
        if not block.get("has_ws"):
            continue
        for no, subj, _cells, line in block["rows"]:
            if is_derived_row(line) or not is_core_ws_each_row(subj):
                continue
            if not ws_passes(line):
                if summary_tier_ok and "📝" in line:
                    continue
                mark = "📝" if "📝" in line else ("⚠️" if "⚠️" in line else "未标记")
                errors.append(
                    f"核心行须双校验：{no} {subj} WS列当前为{mark}，"
                    f"须 ✅/🔗/📄（或补全验证汇总表按年分层，见 06-全面交叉校验清单 §3.2）"
                )

    def matches_ws_group(subject: str, group_name: str) -> bool:
        s = subject.replace("*", "").strip()
        if is_ws_excluded_subject(subject):
            return False
        if group_name == "现金":
            return subject_matches(subject, keywords) and "净增加" not in s
        if group_name == "总负债":
            return "总负债" in s or s == "负债合计"
        if group_name == "资产总计":
            return "资产总计" in s or "资产总额" in s
        return False

    for group_name, keywords in CORE_WS_GROUP_AT_LEAST_ONE:
        ok = False
        for block in blocks:
            if not block.get("has_ws"):
                continue
            for _no, subj, _cells, line in block["rows"]:
                if not matches_ws_group(subj, group_name):
                    continue
                if ws_passes(line):
                    ok = True
                    break
            if ok:
                break
        if not ok:
            errors.append(
                f"核心组须双校验：「{group_name}」在含 WS 列的表中须至少一行 ✅/🔗/📄"
            )


def check_a_cf_section(text: str, errors: list):
    if not re.search(r"A-CF|A-CF：|合并现金流量表|现金流量表", text, re.I):
        errors.append("缺 A-CF 区块：溯源表须含 A-CF（合并现金流量表）章节")
        return
    rows = parse_rows(text)
    ocf_kw = MANDATORY_YEAR_GROUPS[2][1]
    capex_kw = MANDATORY_YEAR_GROUPS[3][1]
    has_ocf = any(no.startswith("A") and subject_matches(subj, ocf_kw) for no, subj, _ in rows)
    has_capex = any(no.startswith("A") and subject_matches(subj, capex_kw) for no, subj, _ in rows)
    if not has_ocf:
        errors.append("A-CF 缺经营现金流行（须含经营活动现金流量净额等核心科目）")
    if not has_capex:
        errors.append("A-CF 缺 CAPEX 行（须含购建固定资产等资本开支科目）")


def check_core_row_completeness(blocks: list[dict], errors: list):
    for block in blocks:
        ycols = year_columns(block["header"])
        if len(ycols) < 5:
            continue
        years_in_table = {y for _, y in ycols}
        if not {"2021", "2022", "2023", "2024", "2025"}.issubset(years_in_table):
            continue
        for no, subject, cells, line in block["rows"]:
            if is_derived_row(line) or not is_core_subject(subject):
                continue
            missing = []
            for col_idx, year in ycols:
                if col_idx >= len(cells) or is_placeholder(cells[col_idx]):
                    missing.append(year)
            if missing:
                errors.append(
                    f"核心科目年份缺口：{no} {subject} 缺 {','.join(missing)}"
                    f"（5年表不得用 — 占位，须从各年年报 PDF 补全或标 ⚠️）"
                )


def check_global_year_coverage(blocks: list[dict], errors: list):
    coverage: dict[str, dict[str, list[str]]] = {
        label: {y: [] for y in ("2021", "2022", "2023", "2024", "2025")}
        for label, _, _ in MANDATORY_YEAR_GROUPS
    }

    for block in blocks:
        ycols = year_columns(block["header"])
        if not ycols:
            continue
        for no, subject, cells, _line in block["rows"]:
            for label, keywords, _full in MANDATORY_YEAR_GROUPS:
                if not subject_matches(subject, keywords):
                    continue
                for col_idx, year in ycols:
                    if col_idx < len(cells) and not is_placeholder(cells[col_idx]):
                        coverage[label][year].append(no)

    for label, _keywords, full_years in MANDATORY_YEAR_GROUPS:
        if full_years:
            missing = [y for y, refs in coverage[label].items() if not refs]
            if missing:
                errors.append(
                    f"必备科目缺少年份覆盖：{label} 缺 {','.join(missing)}"
                    f"（须在 A 区从 PDF 补全，不可留 —）"
                )
        elif not any(refs for refs in coverage[label].values()):
            errors.append(f"必备科目缺失：{label}（A 区须至少一行含 PDF 页码的股本数据）")


CROSS_VAL_SUMMARY_KEYWORDS = ["WebSearch 验证汇总", "验证汇总", "交叉校验汇总"]
WS_MARKS = ("✅", "🔗", "📄", "📝", "⚠️", "🔴", "🟡")
A_CLASS_SUMMARY_ROW_KEYWORDS = [
    "营业收入", "归母", "净利润", "经营", "现金流", "OCF",
    "CAPEX", "购建", "股息", "派息", "分红",
]
DIV_TOTAL_KEYWORDS = ["合计", "全年", "总计"]
DIV_MID_KEYWORDS = ["中期", "特别", "末期"]


def is_a_class_summary_subject(subject: str) -> bool:
    s = subject.replace("*", "").strip()
    if "股息率" in s or "PE" in s.upper():
        return False
    if "营业收入" in s or "营收" in s:
        return True
    if "归母" in s:
        return True
    if ("经营" in s or "OCF" in s) and ("CF" in s or "现金流" in s or "OCF" in s):
        return True
    if "CAPEX" in s or "购建" in s:
        return True
    if "现金" in s and "现金流" not in s:
        return True
    if "负债" in s:
        return True
    if "资产总计" in s or "资产总" in s:
        return True
    if "股息" in s or "派息" in s:
        return True
    if "分红" in s or "支付率" in s:
        return True
    return False


def extract_cell_ws_mark(cell: str) -> str | None:
    v = cell.strip()
    if v in ("—", "–", "-", ""):
        return "—"
    for m in WS_MARKS:
        if m in v:
            return m
    return None


def year_mark_allowed(year: str, mark: str | None) -> tuple[bool, bool]:
    """A 类验证汇总格：(通过, 仅警告)."""
    if mark == "—":
        return True, False
    if mark is None or mark in ("⚠️", "🔴", "🟡"):
        return False, False
    if year == "2021":
        return mark in ("📝", "✅", "🔗", "📄"), False
    if year in ("2022", "2023", "2024"):
        return mark in ("✅", "🔗", "📄"), False
    if year == "2025":
        if mark == "🔗":
            return True, True
        return mark in ("✅", "📄"), False
    return True, False


def parse_validation_summary_table(text: str) -> tuple[list[str], list[tuple[str, dict[str, str | None]]]] | None:
    """解析验证汇总表 → (年份列, [(科目, {年:标记})])."""
    start = -1
    for k in CROSS_VAL_SUMMARY_KEYWORDS:
        pos = text.find(k)
        if pos >= 0:
            start = pos
            break
    if start < 0:
        return None

    zone = text[start:]
    lines = [ln.strip() for ln in zone.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return None

    year_cols: list[tuple[int, str]] = []
    rows: list[tuple[str, dict[str, str | None]]] = []
    header_parsed = False

    for ln in lines:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if is_separator_row(cells):
            continue
        if not header_parsed:
            for i, c in enumerate(cells):
                m = YEAR_HEADER_RE.search(c)
                if m:
                    year_cols.append((i, m.group(0)))
            if year_cols:
                header_parsed = True
            continue
        if not cells:
            continue
        subject = cells[0].replace("*", "").strip()
        if not subject or subject in ("科目", "来源"):
            continue
        if not is_a_class_summary_subject(subject):
            continue
        year_marks: dict[str, str | None] = {}
        for col_idx, year in year_cols:
            if col_idx < len(cells):
                year_marks[year] = extract_cell_ws_mark(cells[col_idx])
        if year_marks:
            rows.append((subject, year_marks))

    years = [y for _, y in year_cols]
    if not years or not rows:
        return None
    return years, rows


def check_ws_summary_year_tier(text: str, errors: list, warnings: list) -> bool:
    """第3层：验证汇总表 A 类按年份分层。返回是否全部通过。"""
    parsed = parse_validation_summary_table(text)
    if parsed is None:
        return False

    _years, rows = parsed
    if not rows:
        warnings.append("验证汇总表无 A 类科目行（营收/归母/经营CF/CAPEX/股息等）")
        return False

    all_ok = True
    for subject, year_marks in rows:
        for year, mark in year_marks.items():
            ok, warn = year_mark_allowed(year, mark)
            if not ok:
                all_ok = False
                errors.append(
                    f"验证汇总年份分层违规：{subject} {year} 标记={mark or '空白'}，"
                    f"规则见 06-全面交叉校验清单 §3.2（2025:✅/📄；2022-24:✅/🔗/📄；2021:可📝）"
                )
            elif warn:
                warnings.append(
                    f"验证汇总建议补强：{subject} {year} 仅 🔗，2025 年建议改为 ✅ 或公告级 📄"
                )
    return all_ok


def check_cross_validation_summary(text: str, warnings: list):
    """第3层：溯源表须含 WebSearch 验证汇总区块，且覆盖核心科目。"""
    if not any(k in text for k in CROSS_VAL_SUMMARY_KEYWORDS):
        warnings.append(
            "缺交叉校验汇总：溯源表须含「WebSearch 验证汇总」区块"
            "（见 docs/ai-rules/06-全面交叉校验清单.md 第3.4节）"
        )
        return

    # 取汇总区块后的表格行做科目覆盖检查
    idx = -1
    for k in CROSS_VAL_SUMMARY_KEYWORDS:
        pos = text.find(k)
        if pos >= 0:
            idx = pos
            break
    if idx < 0:
        return

    summary_zone = text[idx: idx + 4000]
    missing = []
    for kw in ["营业收入", "归母", "经营", "CAPEX", "购建", "现金", "负债", "资产总计", "股息", "派息"]:
        if kw == "经营" and not any(x in summary_zone for x in ("经营", "现金流", "OCF")):
            missing.append("经营CF")
        elif kw == "CAPEX" and "CAPEX" not in summary_zone and "购建" not in summary_zone:
            missing.append("CAPEX")
        elif kw == "负债" and "负债" not in summary_zone:
            missing.append("总负债")
        elif kw == "股息" and "股息" not in summary_zone and "派息" not in summary_zone:
            missing.append("每股股息")
        elif kw not in ("经营", "CAPEX", "负债", "股息") and kw not in summary_zone:
            if kw == "归母" and "归母" not in summary_zone and "净利润" not in summary_zone:
                missing.append("归母净利")

    if missing:
        deduped = list(dict.fromkeys(missing))
        warnings.append(
            f"验证汇总表缺核心科目：{','.join(deduped)}"
            f"（见 06-全面交叉校验清单 第3.4节）"
        )


def check_dividend_structure(text: str, warnings: list):
    """第2层 2.2：A-DIV 须区分年度/中期/合计，禁止仅录年度预案。"""
    if "A-DIV" not in text and "分红数据" not in text:
        return

    div_zone = text
    if "A-DIV" in text:
        div_zone = text[text.find("A-DIV"): text.find("A-NOTE") if "A-NOTE" in text else len(text)]

    has_annual = any(k in div_zone for k in ("年度每股", "年度分红", "末期每股"))
    has_total = any(k in div_zone for k in DIV_TOTAL_KEYWORDS)
    has_mid = any(k in div_zone for k in DIV_MID_KEYWORDS)

    # 年报提及中期/特别分红但溯源表无对应行
    mentions_mid = any(k in text for k in ("中期利润分配", "回报股东特别分红", "两次分红", "中期/特别"))
    if mentions_mid and has_annual and not (has_total or has_mid):
        warnings.append(
            "分红结构疑似不完整：年报提及中期/特别分红，但 A-DIV 缺「中期/特别」或「合计」行"
            f"（见 06-全面交叉校验清单 第2.2节）"
        )

    # 仅有年度行、无合计行（即使无中期，全年=年度也应标明合计）
    if has_annual and not has_total and "每股股息合计" not in div_zone and "每股派息合计" not in div_zone:
        if any(k in div_zone for k in ("每股现金红利", "年度每股股息", "年度每股派息")):
            warnings.append(
                "分红结构建议补「每股股息合计」行：禁止仅用 p2 年度预案代表全年股息"
            )


def check_report_rationality(report: Path, warnings: list):
    """第4层：终稿报告建议含合理性交叉校验记录。"""
    text = report.read_text(encoding="utf-8")
    if "终稿" not in text and "V1.0" not in text:
        return
    if not any(k in text for k in ("合理性交叉校验", "合理性校验", "第4层")):
        warnings.append(
            "终稿缺合理性交叉校验：报告验收记录须含股息率/支付率/累计分红等市场合理性核对"
            f"（见 docs/ai-rules/06-全面交叉校验清单.md 第4.2节）"
        )


def check_report_quality(report: Path, warnings: list):
    text = report.read_text(encoding="utf-8")
    for label, keys in REPORT_SECTIONS:
        if not any(k in text for k in keys):
            warnings.append(f"报告缺小节：{label}（历史遗漏点，请确认是否需补写）")
    lines = text.splitlines()
    if any(k in text for k in BUY_SECTION_KEYWORDS):
        ctx_lines = []
        for i, ln in enumerate(lines):
            if any(k in ln for k in BUY_SECTION_KEYWORDS):
                ctx_lines.extend(lines[i:i + 16])
        ctx = "\n".join(ctx_lines)
        if not any(ch in ctx for ch in FORMULA_CHARS):
            warnings.append(
                "买入区间疑似无公式：买入价应展示 公式=代入值=结果（如 (倍数×FCF−净现金)÷股数÷汇率）"
            )


def parse_rows(text: str):
    rows = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        no = cells[0]
        if ROW_NO_RE.match(no):
            rows.append((no, cells[1], line))
    return rows


def main() -> int:
    if len(sys.argv) < 2:
        print("[USAGE] python scripts/check_report_ready.py <股票代码|溯源表路径>")
        return 1

    table = find_table(sys.argv[1])
    print("=" * 60)
    print("[CHECK] 报告就绪门禁校验 (V5.5.18)")
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

    blocks = parse_table_blocks(text)
    print(f"[OK]   解析到 {len(blocks)} 个 A 区表格块")

    errors, warnings = [], []

    for no, subj in [(n, s) for n, s, ln in rows if "🔴" in ln]:
        errors.append(f"未解决🔴：{no} {subj}（差值≥5%，必须核实修正）")

    warn_rows = [(n, s) for n, s, ln in rows if "⚠️" in ln]
    for no, subj in warn_rows:
        warnings.append(f"待验证⚠️：{no} {subj}")
    if len(warn_rows) > MAX_WARN_ROWS:
        warnings.append(f"⚠️ 共 {len(warn_rows)} 条，超过建议上限 {MAX_WARN_ROWS} 条，建议对话1内补验")

    check_header_contract(text, errors)
    check_reconciliation(text, errors)
    summary_tier_ok = check_ws_summary_year_tier(text, errors, warnings)
    check_cross_validation_summary(text, warnings)
    check_dividend_structure(text, warnings)
    check_core_ws_validation(blocks, errors, summary_tier_ok)

    for no, subj, line in rows:
        if not no.startswith("A") or is_derived_row(line):
            continue
        if is_core_subject(subj) and not PAGE_RE.search(line):
            errors.append(f"核心科目缺页码：{no} {subj}（A区必须标注 p+页码）")

    for no, subj, line in rows:
        if is_derived_row(line) or any(k in subj for k in MARKET_KEYWORDS):
            continue
        low_line = line.lower()
        if any(k in low_line for k in FAB_KEYWORDS) and not PAGE_RE.search(line):
            errors.append(
                f"来源造假：{no} {subj}（疑用网络搜索且无PDF页码，核心数据须取年报原文）"
            )
        if any(kw in subj for kw in CORE_KEYWORDS + CURRENCY_CORE_EXTRA):
            if any(c in low_line for c in CURRENCY_FLAG):
                warnings.append(f"币种存疑：{no} {subj}（核心科目疑用港币，应取年报人民币原文）")

    check_a_cf_section(text, errors)
    check_core_row_completeness(blocks, errors)
    check_global_year_coverage(blocks, errors)

    report = find_report(sys.argv[1])
    if report is not None and report.exists():
        print(f"[OK]   报告：{report}")
        check_report_quality(report, warnings)
        check_report_rationality(report, warnings)

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
