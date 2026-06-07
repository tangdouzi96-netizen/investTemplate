# -*- coding: utf-8 -*-
"""中国食品(00506.HK) 年报 PDF 全文 dump + 报表定位"""
import fitz, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

PDF_DIR = r"d:\Project\investTemplate\07-分析输出\中国食品"
DUMP_DIR = r"d:\Project\investTemplate\scripts\dumps\00506"
os.makedirs(DUMP_DIR, exist_ok=True)

YEARS = [2021, 2022, 2023, 2024, 2025]
# Map year to filename pattern
FILE_MAP = {}
for f in os.listdir(PDF_DIR):
    if not f.endswith('.pdf'):
        continue
    for y in YEARS:
        if str(y) in f:
            FILE_MAP[y] = os.path.join(PDF_DIR, f)
            break

print("=" * 80)
print("PDF 文件映射:")
for y in sorted(FILE_MAP.keys()):
    print(f"  {y}: {os.path.basename(FILE_MAP[y])}")

# Keywords for locating financial statements (HK stock, Chinese reports)
# 中国食品 uses Chinese reports
BS_KEYWORDS = ['综合财务状况表', '合并财务状况表', '綜合財務狀況表', '合併財務狀況表',
               'CONSOLIDATED STATEMENT OF FINANCIAL POSITION',
               '合并资产负债表', '合併資產負債表', '綜合資產負債表']
PL_KEYWORDS = ['综合损益表', '合并损益表', '綜合損益表', '合併損益表', '综合收益表', '綜合收益表',
               'CONSOLIDATED STATEMENT OF PROFIT OR LOSS',
               '合并利润表', '合併利潤表', '綜合利潤表']
CF_KEYWORDS = ['综合现金流量表', '合并现金流量表', '綜合現金流量表', '合併現金流量表',
               'CONSOLIDATED STATEMENT OF CASH FLOWS',
               'CONSOLIDATED CASH FLOW STATEMENT']
# Fallback for CF
CF_FALLBACK = ['经营活动（所用）/产生的现金净额', '经营活动产生的现金流量', '經營活動產生的現金流量',
               'Cash generated from operations']
# Notes section
NOTE_KEYWORDS = ['财务报表附注', '財務報表附注', 'NOTES TO THE FINANCIAL STATEMENTS',
                 '附注：', '受限制', '所有权或使用权受到限制的资产',
                 '所有權或使用權受到限制的資產']
DIV_KEYWORDS = ['股息', '股利', '每股', 'DIVIDEND', '分红', '利润分配', '末期股息',
                '派息', '末期', '中期股息']

def search_pages(doc, keywords, max_results=20):
    """Search for keywords across all pages, return {page_num: [matched_lines]}"""
    results = {}
    for pg in range(doc.page_count):
        text = doc[pg].get_text("text")
        lines = text.split('\n')
        for line in lines:
            for kw in keywords:
                if kw.lower() in line.lower():
                    if pg+1 not in results:
                        results[pg+1] = []
                    results[pg+1].append(line.strip()[:150])
                    break
        if len(results) >= max_results:
            break
    return results

def find_statement_pages(doc, keywords, fallback=None):
    """Find pages containing consolidated financial statements.
    Returns list of page numbers (1-indexed)."""
    pages = []
    for pg in range(doc.page_count):
        text = doc[pg].get_text("text")
        # Check if page contains consolidated statement header
        for kw in keywords:
            if kw in text:
                # Make sure it's not just a table of contents reference
                # Check that the page has actual statement content (numbers)
                lines = text.split('\n')
                num_count = sum(1 for l in lines if re.search(r'\d{3,}', l))
                if num_count >= 5:  # Must have at least 5 lines with numbers
                    pages.append(pg + 1)
                    break
    if not pages and fallback:
        for pg in range(doc.page_count):
            text = doc[pg].get_text("text")
            for kw in fallback:
                if kw in text:
                    pages.append(pg + 1)
                    break
            if pages:
                break
    return pages

def dump_pages(doc, start_page, num_pages, out_path):
    """Dump specified pages to text file"""
    with open(out_path, 'w', encoding='utf-8') as f:
        for pg in range(start_page - 1, min(start_page - 1 + num_pages, doc.page_count)):
            text = doc[pg].get_text("text")
            f.write(f"\n{'='*60}\n")
            f.write(f"📄 第{pg+1}页\n{'='*60}\n")
            f.write(text)
    return out_path

# Main scan
for year in sorted(FILE_MAP.keys()):
    fp = FILE_MAP[year]
    print(f"\n{'='*80}")
    print(f"📊 {year}年年报: {os.path.basename(fp)}")
    doc = fitz.open(fp)
    print(f"  总页数: {doc.page_count}")

    # Find BS pages
    bs_pages = find_statement_pages(doc, BS_KEYWORDS)
    print(f"  BS 页: {bs_pages}")

    # Find PL pages
    pl_pages = find_statement_pages(doc, PL_KEYWORDS)
    print(f"  PL 页: {pl_pages}")

    # Find CF pages
    cf_pages = find_statement_pages(doc, CF_KEYWORDS, CF_FALLBACK)
    print(f"  CF 页: {cf_pages}")

    # Find notes
    note_pages = search_pages(doc, NOTE_KEYWORDS, max_results=5)
    print(f"  附注相关页: {list(note_pages.keys())[:10]}")

    # Find dividend
    div_pages = search_pages(doc, DIV_KEYWORDS, max_results=10)
    print(f"  股息相关页: {list(div_pages.keys())[:10]}")

    # Dump key pages: BS, PL, CF + surrounding context
    dump_start = max(1, min(bs_pages + pl_pages + cf_pages) - 2) if (bs_pages + pl_pages + cf_pages) else 1
    dump_end = min(doc.page_count, max(bs_pages + pl_pages + cf_pages) + 4) if (bs_pages + pl_pages + cf_pages) else min(doc.page_count, dump_start + 20)

    # Dump full report for detailed search later
    # First dump the financial statements area
    if bs_pages:
        for bp in bs_pages:
            dump_pages(doc, bp, 3, os.path.join(DUMP_DIR, f"{year}_BS_p{bp}.txt"))
    if pl_pages:
        for pp in pl_pages:
            dump_pages(doc, pp, 3, os.path.join(DUMP_DIR, f"{year}_PL_p{pp}.txt"))
    if cf_pages:
        for cp in cf_pages:
            dump_pages(doc, cp, 3, os.path.join(DUMP_DIR, f"{year}_CF_p{cp}.txt"))

    # Also search for specific important items
    important_keywords = [
        '营业收入', '營業收入', 'Revenue',
        '归母', '歸母', '本公司拥有人', '本公司擁有人',
        '经营活', '經營活', 'Operating activities',
        '购建', '購建', 'Purchase of property', 'Capital expenditure',
        '资本开支', '資本開支',
        '货币资金', '貨幣資金', '现金及现金等价物', '現金及現金等價物',
        '资产总计', '資產總計', 'Total assets',
        '负债总计', '負債總計', 'Total liabilities',
        '股本', 'Share capital',
        '股息', 'Dividend',
        '受限制', 'restricted', '抵押', 'Pledged',
    ]

    for kw in important_keywords:
        found = search_pages(doc, [kw], max_results=5)
        if found:
            brief = {k: v[0][:80] for k, v in list(found.items())[:3]}
            # print(f"  '{kw}' → {brief}")

    doc.close()

print(f"\n✅ Dump 完成，文件写入: {DUMP_DIR}")
