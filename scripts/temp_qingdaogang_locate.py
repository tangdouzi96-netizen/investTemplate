"""青岛港年报 - 定位合并三大报表页码"""
import fitz
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

base = r"d:\Project\investTemplate\07-分析输出\青岛港年报"

pdfs = {
    2021: os.path.join(base, "青岛港：青岛港国际股份有限公司2021年年度报告.pdf"),
    2022: os.path.join(base, "青岛港：2022年度报告.pdf"),
    2023: os.path.join(base, "青岛港：2023年度报告.pdf"),
    2024: os.path.join(base, "青岛港：2024年度报告.pdf"),
    2025: os.path.join(base, "青岛港：2025年度报告.pdf"),
}

# 港股年报定位关键词（中英文混合）
BS_KEYWORDS_CN = ["合并资产负债表", "综合财务状况表", "CONSOLIDATED STATEMENT OF FINANCIAL POSITION",
                   "CONSOLIDATED BALANCE SHEET", "合併資產負債表", "合併財務狀況表"]
PL_KEYWORDS_CN = ["合并利润表", "综合损益表", "CONSOLIDATED STATEMENT OF PROFIT OR LOSS",
                   "CONSOLIDATED INCOME STATEMENT", "合併利潤表", "合併損益表",
                   "CONSOLIDATED STATEMENT OF COMPREHENSIVE INCOME"]
CF_KEYWORDS_CN = ["合并现金流量表", "综合现金流量表", "CONSOLIDATED STATEMENT OF CASH FLOWS",
                   "CONSOLIDATED CASH FLOW STATEMENT", "合併現金流量表"]
NOTE_KEYWORDS = ["财务报表附注", "NOTES TO THE FINANCIAL STATEMENTS", "財務報表附註"]

for year, path in sorted(pdfs.items()):
    if not os.path.exists(path):
        print(f"\n{'='*60}")
        print(f"❌ {year}: 文件不存在 {path}")
        continue

    doc = fitz.open(path)
    total_pages = doc.page_count
    print(f"\n{'='*60}")
    print(f"📄 {year}年年报: {os.path.basename(path)} (共{total_pages}页)")

    bs_pages = []
    pl_pages = []
    cf_pages = []
    note_pages = []

    for pg in range(total_pages):
        text = doc[pg].get_text("text")
        text_upper = text.upper()

        # BS
        for kw in BS_KEYWORDS_CN:
            if kw.upper() in text_upper:
                # 排除母公司报表
                if "母公司" not in text[:500] and "PARENT" not in text[:500].upper():
                    bs_pages.append(pg + 1)
                    break

        # PL
        for kw in PL_KEYWORDS_CN:
            if kw.upper() in text_upper:
                if "母公司" not in text[:500] and "PARENT" not in text[:500].upper():
                    pl_pages.append(pg + 1)
                    break

        # CF
        for kw in CF_KEYWORDS_CN:
            if kw.upper() in text_upper:
                if "母公司" not in text[:500] and "PARENT" not in text[:500].upper():
                    cf_pages.append(pg + 1)
                    break

        # Notes
        for kw in NOTE_KEYWORDS:
            if kw.upper() in text_upper:
                note_pages.append(pg + 1)
                break

    print(f"  BS 候选页: {bs_pages}")
    print(f"  PL 候选页: {pl_pages}")
    print(f"  CF 候选页: {cf_pages}")
    print(f"  附注首页: {note_pages[:3]}...")

    # 搜索关键科目确认页码
    # 搜索"资产总计" / "Total assets"
    for pg in range(total_pages):
        text = doc[pg].get_text("text")
        if ("资产总计" in text or "资产总额" in text) and "母公司" not in text[:300]:
            if pg + 1 not in bs_pages:
                bs_pages.append(pg + 1)

    # 搜索"营业收入"
    for pg in range(total_pages):
        text = doc[pg].get_text("text")
        if "营业收入" in text and "营业成本" in text and "母公司" not in text[:300]:
            if pg + 1 not in pl_pages:
                pl_pages.append(pg + 1)

    # 搜索"经营活动" + "现金流量"
    for pg in range(total_pages):
        text = doc[pg].get_text("text")
        if ("经营活动" in text and "现金流量" in text) and "母公司" not in text[:300]:
            if pg + 1 not in cf_pages:
                cf_pages.append(pg + 1)

    print(f"  → BS 最终候选: {sorted(set(bs_pages))}")
    print(f"  → PL 最终候选: {sorted(set(pl_pages))}")
    print(f"  → CF 最终候选: {sorted(set(cf_pages))}")

    doc.close()
