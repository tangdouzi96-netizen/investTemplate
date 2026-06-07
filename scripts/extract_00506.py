# -*- coding: utf-8 -*-
"""中国食品(00506.HK) 精确财报数据提取 - 全部5年"""
import fitz, os, re, json, sys
sys.stdout.reconfigure(encoding='utf-8')

PDF_DIR = r"d:\Project\investTemplate\07-分析输出\中国食品"
FILE_MAP = {
    2021: os.path.join(PDF_DIR, "中国食品：2021年报.pdf"),
    2022: os.path.join(PDF_DIR, "中国食品：2022年报.pdf"),
    2023: os.path.join(PDF_DIR, "中国食品：2023年报.pdf"),
    2024: os.path.join(PDF_DIR, "中国食品：2024年度报告.pdf"),
    2025: os.path.join(PDF_DIR, "中国食品：2025年度报告.pdf"),
}

def to_yi(val_rmb_thousands):
    """人民币千元 → 亿元"""
    return round(val_rmb_thousands / 100_000, 2)

def find_pl_page(doc):
    """Find consolidated PL page"""
    for pg in range(doc.page_count):
        text = doc[pg].get_text("text")
        if ('CONSOLIDATED STATEMENT OF PROFIT OR LOSS' in text or
            '綜合損益及其他全面收益表' in text or
            '綜合損益表' in text or '综合损益表' in text):
            # Must not be just TOC - check for Revenue keyword
            if 'Revenue' in text and 'RMB' in text:
                return pg + 1
    return None

def find_bs_pages(doc):
    """Find consolidated BS pages (usually 2 pages)"""
    pages = []
    for pg in range(doc.page_count):
        text = doc[pg].get_text("text")
        if ('CONSOLIDATED STATEMENT OF FINANCIAL POSITION' in text or
            '綜合財務狀況表' in text or '综合财务状况表' in text):
            if 'RMB' in text and ('Non-current assets' in text or 'Total assets' in text or 'Current assets' in text):
                pages.append(pg + 1)
    return sorted(set(pages))

def find_cf_pages(doc):
    """Find consolidated CF pages (usually 2-3 pages)"""
    pages = []
    for pg in range(doc.page_count):
        text = doc[pg].get_text("text")
        if ('CONSOLIDATED STATEMENT OF CASH FLOWS' in text or
            '綜合現金流量表' in text or '综合现金流量表' in text):
            if 'OPERATING ACTIVITIES' in text or 'NET CASH FROM OPERATING' in text or '经营活' in text:
                pages.append(pg + 1)
    return sorted(set(pages))

def extract_numbers_from_page(doc, page_num):
    """Extract all number pairs from a page (year columns)"""
    text = doc[page_num - 1].get_text("text")
    return text

def search_value_in_text(text, keywords, year_str='2025'):
    """Search for a specific line and extract numeric value"""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        for kw in keywords:
            if kw.lower() in line.lower():
                # Look at nearby lines for numbers
                for j in range(max(0,i-2), min(len(lines), i+5)):
                    # Try to find a number that looks like the value
                    pass
    return None

print("=" * 100)
print("中国食品(00506.HK) 5年财报数据提取")
print("=" * 100)

all_data = {}

for year in sorted(FILE_MAP.keys(), reverse=True):
    fp = FILE_MAP[year]
    print(f"\n{'='*80}")
    print(f"📊 {year}年")
    doc = fitz.open(fp)

    pl_pg = find_pl_page(doc)
    bs_pgs = find_bs_pages(doc)
    cf_pgs = find_cf_pages(doc)

    print(f"  PL页: {pl_pg}")
    print(f"  BS页: {bs_pgs}")
    print(f"  CF页: {cf_pgs}")

    # Dump PL page
    if pl_pg:
        pl_text = extract_numbers_from_page(doc, pl_pg)
        print(f"\n  --- PL p{pl_pg} 全文 ---")
        for line in pl_text.split('\n'):
            line = line.strip()
            if line and any(kw in line.lower() for kw in [
                'revenue', '收入', 'cost of sales', '銷售成本', 'gross profit', '毛利',
                'other income', '其他收入', 'distribution', '分銷', 'administrative',
                '行政', 'operating profit', '經營溢利', 'finance cost', '融資成本',
                'share of results', '應佔聯營', 'profit before tax', '除稅前溢利',
                'income tax', '所得稅', 'profit and total', '年內溢利',
                'owners of the company', '本公司擁有人', 'non-controlling',
                '非控股權益', 'earnings per share', '每股盈利',
            ]):
                print(f"    {line[:150]}")

    # Dump BS pages
    for bsp in (bs_pgs or []):
        bs_text = extract_numbers_from_page(doc, bsp)
        print(f"\n  --- BS p{bsp} ---")
        for line in bs_text.split('\n'):
            line = line.strip()
            if line and any(kw in line.lower() for kw in [
                'non-current assets', '非流動資產', 'current assets', '流動資產',
                'property, plant', '物業、廠房', 'right-of-use', '使用權',
                'intangible', '無形', 'deferred tax', '遞延稅項',
                'inventories', '存貨', 'trade receivables', '應收貿易',
                'restricted bank', '受限制銀行', 'cash and cash', '現金及現金等值',
                'total assets', '資產總計', 'current liabilities', '流動負債',
                'non-current liabilities', '非流動負債', 'total liabilities', '負債總計',
                'net assets', '資產淨額', 'share capital', '股本',
                'share premium', '股份溢價', 'equity attributable', '本公司擁有人應佔',
                'non-controlling', '非控股權益', 'total equity', '權益總額',
                'trade and bills', '應付貿易', 'other payables', '其他應付款',
                'contract liabilities', '合約負債', 'lease liabilities', '租賃負債',
                'deferred income', '遞延收入',
            ]):
                print(f"    {line[:150]}")

    # Dump CF pages
    for cfp in (cf_pgs or []):
        cf_text = extract_numbers_from_page(doc, cfp)
        print(f"\n  --- CF p{cfp} ---")
        for line in cf_text.split('\n'):
            line = line.strip()
            if line and any(kw in line.lower() for kw in [
                'net cash from operating', '經營活動所得現金淨額',
                'net cash used in investing', '投資活動所用現金淨額',
                'net cash used in financing', '融資活動所用現金淨額',
                'net increase in cash', '現金及現金等值項目增加淨額',
                'cash and cash equivalents at 1 january', '於1月1日之現金',
                'cash and cash equivalents at 31 december', '於12月31日之現金',
                'purchase of property', '購買物業', 'payments for intangible',
                '支付無形', 'payments for right-of-use', '支付使用權',
                'dividends paid', '已付股息', 'repayment of lease',
                '償還租賃', 'interest received', '已收利息',
                'income taxes paid', '已付所得稅',
                'cash generated from operations', '經營業務所得現金',
            ]):
                print(f"    {line[:150]}")

    doc.close()

print("\n\n✅ 提取完成")
