# -*- coding: utf-8 -*-
"""Extract insurance investment data from 中国平安 annual reports."""
import fitz, sys, re
sys.stdout.reconfigure(encoding='utf-8')

files = {
    2021: '中国平安_601318_2021年年报_2022-03-17.pdf',
    2022: '中国平安_601318_2022年年报_2023-03-15.pdf',
    2023: '中国平安_601318_2023年年报_2024-03-21.pdf',
    2024: '中国平安_601318_2024年年报_2025-03-19.pdf',
    2025: '中国平安_601318_2025年年报_2026-03-26.pdf',
}

BASE = r'07-分析输出\中国平安\年报'

for yr in [2021, 2022, 2023, 2024, 2025]:
    doc = fitz.open(f'{BASE}/{files[yr]}')
    print(f'\n=== {yr} ===')

    # Search for insurance investment portfolio size
    found_portfolio = False
    for pg in range(15, 55):
        text = doc[pg].get_text('text')
        patterns = [
            (r'保险资金投资组合[^0-9]*([\d,.]+\s*万亿)', 'p'),
            (r'投资组合规模[^0-9]*([\d,.]+\s*万亿)', 'p'),
            (r'[\d,.]+\s*万亿[^。]*保险资金', 'p'),
            (r'保险资金[^。]*([\d,.]+\s*万亿)', 'p'),
        ]
        for pat, _ in patterns:
            m = re.search(pat, text)
            if m:
                ctx = text[max(0, m.start()-30):m.end()+100].replace('\n', ' ')
                print(f'  投资组合 p{pg+1}: {ctx[:200]}')
                found_portfolio = True
                break
        if found_portfolio:
            break
    if not found_portfolio:
        # Try searching without 万亿
        for pg in range(15, 55):
            text = doc[pg].get_text('text')
            if '保险资金' in text and '投资组合' in text:
                idx = text.find('保险资金投资组合')
                if idx == -1:
                    idx = text.find('投资组合')
                ctx = text[max(0, idx-50):idx+300].replace('\n', ' ')
                # Find number + 亿
                m = re.search(r'([\d,.]{4,})\s*亿元', ctx)
                if m:
                    print(f'  投资组合 p{pg+1}: {ctx[:250]}')
                    found_portfolio = True
                    break

    # Search for investment yield
    found_yield = False
    for pg in range(15, 55):
        text = doc[pg].get_text('text')
        for kw in ['总投资收益率', '综合投资收益率', '净投资收益率']:
            if kw in text:
                idx = text.find(kw)
                ctx = text[max(0, idx-80):idx+250].replace('\n', ' ')
                print(f'  投资收益率 p{pg+1}: {ctx[:250]}')
                found_yield = True
                break
        if found_yield:
            break

    # Search for 现金分红总额
    for pg in range(10, 20):
        text = doc[pg].get_text('text')
        if '分红' in text and '亿' in text and ('总额' in text or '共计' in text or '合计' in text):
            # find the dividend total
            m = re.search(r'现金分红[^。]*?([\d,.]+)\s*亿元', text)
            if not m:
                m = re.search(r'派发[^。]*?([\d,.]+)\s*亿元', text)
            if not m:
                m = re.search(r'现金股利[^。]*?([\d,.]+)\s*亿元', text)
            if m:
                ctx = text[max(0, m.start()-30):m.end()+100].replace('\n', ' ')
                print(f'  分红总额 p{pg+1}: {ctx[:250]}')
            break

    doc.close()

print('\nDone')
