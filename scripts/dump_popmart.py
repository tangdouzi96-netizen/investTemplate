"""
泡泡玛特 09992 — 五年年报关键页 dump
用法: python scripts/dump_popmart.py
输出: 07-分析输出/泡泡玛特/dump_202X.txt (2021-2025)
"""
import fitz
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = r"d:\Project\investTemplate\07-分析输出\泡泡玛特"
YEARS = [2021, 2022, 2023, 2024, 2025]

# 港股定位关键词
KEYWORDS = {
    "PL": [
        "CONSOLIDATED STATEMENT OF PROFIT OR LOSS",
        "综合损益表",
        "CONSOLIDATED INCOME STATEMENT",
        "综合收益表",
        "损益表",
    ],
    "BS": [
        "CONSOLIDATED STATEMENT OF FINANCIAL POSITION",
        "综合财务状况表",
        "CONSOLIDATED BALANCE SHEET",
        "综合资产负债表",
        "资产负债表",
    ],
    "CF": [
        "CONSOLIDATED STATEMENT OF CASH FLOWS",
        "综合现金流量表",
        "CONSOLIDATED CASH FLOW STATEMENT",
        "现金流量表",
    ],
    "SUMMARY": [
        "财务摘要",
        "FINANCIAL SUMMARY",
        "FINANCIAL HIGHLIGHTS",
        "主要财务数据",
        "五年财务摘要",
    ],
    "DIVIDEND": [
        "股息",
        "DIVIDEND",
        "末期股息",
        "FINAL DIVIDEND",
        "利润分配",
    ],
    "IP_SEGMENT": [
        "THE MONSTERS",
        "MOLLY",
        "SKULLPANDA",
        "IP",
        "艺术家",
        "ARTIST",
    ],
}

def find_pages(doc, keywords, exclude_parent=True):
    """搜索包含任一关键词的页码（港股：排除只含"母公司"的页）"""
    pages = set()
    for pg in range(doc.page_count):
        text = doc[pg].get_text("text")
        # 排除母公司报表
        if exclude_parent and "母公司" in text[:500]:
            continue
        for kw in keywords:
            if kw in text:
                pages.add(pg)
                break
    return sorted(pages)

def dump_pages(doc, pages, out_path, section_label):
    """将指定页面 dump 到文件"""
    with open(out_path, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"📊 {section_label}\n")
        f.write(f"{'='*80}\n")
        for pg_num in pages:
            text = doc[pg_num].get_text("text")
            f.write(f"\n{'─'*60}\n")
            f.write(f"📄 PDF 物理页 {pg_num+1}\n{'─'*60}\n")
            f.write(text)

def main():
    for year in YEARS:
        pdf_name = f"泡泡玛特：二零二{['','一','二','三','四','五'][year-2020]}年年报.pdf"
        pdf_path = os.path.join(BASE, pdf_name)
        if not os.path.exists(pdf_path):
            print(f"❌ 文件不存在: {pdf_path}")
            continue

        print(f"\n{'='*60}")
        print(f"📖 处理: {pdf_name}")
        print(f"{'='*60}")

        doc = fitz.open(pdf_path)
        print(f"  总页数: {doc.page_count}")

        out_path = os.path.join(BASE, f"dump_{year}.txt")
        # 清空旧文件
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(f"# 泡泡玛特 {year}年年报 dump\n")
            f.write(f"# 文件: {pdf_name}\n")
            f.write(f"# 总页数: {doc.page_count}\n\n")

        # 1. 财务摘要
        summary_pages = find_pages(doc, KEYWORDS["SUMMARY"])
        if summary_pages:
            dump_pages(doc, summary_pages, out_path, f"财务摘要 (共{len(summary_pages)}页)")
            print(f"  财务摘要: {[p+1 for p in summary_pages]}")

        # 2. PL
        pl_pages = find_pages(doc, KEYWORDS["PL"])
        if pl_pages:
            dump_pages(doc, pl_pages, out_path, f"综合损益表 (共{len(pl_pages)}页)")
            print(f"  损益表: {[p+1 for p in pl_pages]}")

        # 3. BS
        bs_pages = find_pages(doc, KEYWORDS["BS"])
        if bs_pages:
            dump_pages(doc, bs_pages, out_path, f"综合财务状况表 (共{len(bs_pages)}页)")
            print(f"  资产负债表: {[p+1 for p in bs_pages]}")

        # 4. CF
        cf_pages = find_pages(doc, KEYWORDS["CF"])
        if cf_pages:
            dump_pages(doc, cf_pages, out_path, f"综合现金流量表 (共{len(cf_pages)}页)")
            print(f"  现金流量表: {[p+1 for p in cf_pages]}")

        # 5. 分红
        div_pages = find_pages(doc, KEYWORDS["DIVIDEND"])
        if div_pages:
            dump_pages(doc, div_pages, out_path, f"股息/分红相关 (共{len(div_pages)}页)")
            print(f"  分红: {[p+1 for p in div_pages]}")

        # 6. IP 分部
        ip_pages = find_pages(doc, KEYWORDS["IP_SEGMENT"], exclude_parent=False)
        if ip_pages:
            # 只取前 3 页（太多页会过大）
            dump_pages(doc, ip_pages[:3], out_path, f"IP分部(前3页,共{len(ip_pages)}页)")
            print(f"  IP分部: {[p+1 for p in ip_pages[:3]]} (共{len(ip_pages)}页)")

        # 7. 附注：受限资产
        restricted_pages = find_pages(doc, ["受限制", "RESTRICTED", "抵押", "PLEDGED", "质押"], exclude_parent=False)
        if restricted_pages:
            dump_pages(doc, restricted_pages[:5], out_path, f"受限资产/抵押(前5页,共{len(restricted_pages)}页)")
            print(f"  受限资产: {[p+1 for p in restricted_pages[:5]]}")

        doc.close()
        print(f"  ✅ 输出: {out_path}")

    print("\n✅ 全部完成")

if __name__ == "__main__":
    main()
