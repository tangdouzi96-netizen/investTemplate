"""从泡泡玛特各年年报提取IP收入分部和门店数"""
import fitz
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = r"d:\Project\investTemplate\07-分析输出\泡泡玛特"

def search_context(doc, keywords, context_lines=2):
    """搜索关键词并返回上下文"""
    results = []
    for pg in range(doc.page_count):
        text = doc[pg].get_text("text")
        lines = text.split('\n')
        for li, line in enumerate(lines):
            for kw in keywords:
                if kw in line:
                    s = max(0, li - context_lines)
                    e = min(len(lines), li + context_lines + 1)
                    results.append({
                        'page': pg + 1,
                        'keyword': kw,
                        'line': line.strip()[:200],
                    })
                    break
    return results

# Search terms
IP_TERMS = ['MOLLY', 'SKULLPANDA', 'DIMOO', 'THE MONSTERS', 'PUCKY', 'CRYBABY',
            '收入', '艺术家IP', '自主IP', '独家IP', '非独家IP', '外采']
STORE_TERMS = ['零售店', '机器人商店', '线下门店', '门店数量', 'retail store',
               '零售門店', '門店', '销售点', '銷售點', '渠道']

for year in [2021, 2022, 2023, 2024, 2025]:
    year_cn = ['','一','二','三','四','五'][year-2020]
    pdf_name = f"泡泡玛特：二零二{year_cn}年年报.pdf"
    pdf_path = os.path.join(BASE, pdf_name)
    if not os.path.exists(pdf_path):
        continue

    print(f"\n{'='*60}")
    print(f"📖 {year}年年报")
    print(f"{'='*60}")

    doc = fitz.open(pdf_path)

    # Search for IP revenue mentions in the MD&A section (pages 10-50 typically)
    ip_hits = search_context(doc, ['收入', '百萬', '亿元', '千元'], context_lines=0)

    # Search for specific IP names with revenue
    for pg in range(min(60, doc.page_count)):
        text = doc[pg].get_text("text")
        # Look for IP revenue tables (MD&A section)
        for ip_name in ['MOLLY', 'SKULLPANDA', 'DIMOO', 'THE MONSTERS', 'PUCKY', 'CRYBABY', 'HIRONO', 'Zsiga', '星星人']:
            if ip_name in text:
                # Find the line with this IP and check nearby lines for numbers
                lines = text.split('\n')
                for li, line in enumerate(lines):
                    if ip_name in line and any(c.isdigit() for c in line):
                        # Print context
                        s = max(0, li-1)
                        e = min(len(lines), li+3)
                        ctx = ' | '.join(lines[s:e])
                        if any(kw in ctx for kw in ['百万', '千', '亿', '%', 'million', 'thousand', 'billion']):
                            print(f"  p{pg+1} [{ip_name}]: {ctx[:300]}")

    # Search for store counts
    for pg in range(min(60, doc.page_count)):
        text = doc[pg].get_text("text")
        for kw in ['零售店', '零售門店', '机器人商店', '機器人商店', '门店数量']:
            if kw in text:
                idx = text.find(kw)
                ctx = text[max(0,idx-50):min(len(text),idx+200)]
                print(f"  p{pg+1} [{kw}]: ...{ctx[:250]}...")

    doc.close()

print("\n✅ 完成")
