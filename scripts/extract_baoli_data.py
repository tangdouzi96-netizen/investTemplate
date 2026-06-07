# -*- coding: utf-8 -*-
"""Extract key financial data from 保利物业 (06049) 2021-2025 annual reports."""
import fitz, sys, re, os
sys.stdout.reconfigure(encoding='utf-8')

BASE = r'07-分析输出\保利物业'
files = {
    2025: '保利物业_06049_2025年年报_2026-04-30.pdf',
    2024: '保利物业_06049_2024年年报_2025-04-28.pdf',
    2023: '保利物业_06049_2023年年报_2024-04-25.pdf',
    2022: '保利物业_06049_2022年年报_2023-04-25.pdf',
    2021: '保利物业_06049_2021年年报_2022-04-19.pdf',
}

def find_page(doc, keyword, start=0, end=None):
    if end is None: end = doc.page_count
    for pg in range(start, min(end, doc.page_count)):
        text = doc[pg].get_text("text")
        if keyword in text and len(text) > 500:
            return pg
    return None

def extract_section(text, keyword, context_lines=8):
    """Extract lines around a keyword."""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if keyword in line:
            return lines[max(0,i-1):min(len(lines),i+context_lines)]
    return []

for yr in [2025, 2024, 2023, 2022, 2021]:
    fp = os.path.join(BASE, files[yr])
    doc = fitz.open(fp)
    print(f'\n{"="*60}')
    print(f'{yr}年年报 ({doc.page_count}页)')

    # Find financial summary page (p5-6 area)
    for pg in range(min(10, doc.page_count)):
        text = doc[pg].get_text('text')
        if '收入（人民幣' in text and '毛利' in text:
            # Extract key lines
            for line in text.split('\n'):
                line = line.strip()
                if any(kw in line for kw in ['收入（','毛利（','毛利率','年內溢利','本公司擁有人','每股基本盈利','現金及銀行','資產總值','權益總額','資產負債率','股東權益回報']):
                    # Find the RMB values
                    vals = re.findall(r'[\d,]+\.?\d*', line)
                    print(f'  {line[:80]}')
            break

    # Find PL page
    for pg in range(70, doc.page_count):
        text = doc[pg].get_text('text')
        if '综合损益' in text and '收入' in text and '人民币千元' in text and len(text) > 500:
            # Extract PL key lines
            lines = text.split('\n')
            for i, line in enumerate(lines):
                stripped = line.strip()
                for kw in ['收入 ','服务成本','毛利 ','销售及分销','行政开支','其他收入','财务收入','财务成本','税前溢利','所得税','年內溢利','本公司擁有人','每股基本']:
                    if stripped.startswith(kw) or kw in stripped:
                        ctx = ' | '.join(l.strip() for l in lines[max(0,i-1):min(len(lines),i+2)])
                        if len(ctx) < 200:
                            print(f'  PL: {ctx[:200]}')
                        break
            break

    # Find BS page
    for pg in range(70, doc.page_count):
        text = doc[pg].get_text('text')
        if '综合财务状况表' in text and '人民币千元' in text and len(text) > 500:
            lines = text.split('\n')
            for target in ['现金及银行结余','贸易应收款项','流动资产','资产总值','贸易应付款项','合同负债','租赁负债','借款','流动资产','非流动资产','非流动负债','权益总额','本公司拥有人']:
                for i, line in enumerate(lines):
                    if target in line.strip() and len(line.strip()) < 150:
                        ctx = ' | '.join(l.strip() for l in lines[max(0,i-1):min(len(lines),i+2)])
                        if len(ctx) < 200:
                            print(f'  BS: {ctx[:200]}')
                            break
            break

    doc.close()
    if yr < 2025:
        print('  (仅提取摘要页数据，完整BS/PL待逐页dump)')
