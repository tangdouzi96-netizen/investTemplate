# -*- coding: utf-8 -*-
"""Extract BS/CF/dividend data from 保利物业 2021-2023 annual reports."""
import fitz, sys, re, os
sys.stdout.reconfigure(encoding='utf-8')

BASE = r'07-分析输出\保利物业'
files = {
    2023: '保利物业_06049_2023年年报_2024-04-25.pdf',
    2022: '保利物业_06049_2022年年报_2023-04-25.pdf',
    2021: '保利物业_06049_2021年年报_2022-04-19.pdf',
}

for yr in [2023, 2022, 2021]:
    fp = os.path.join(BASE, files[yr])
    doc = fitz.open(fp)
    print(f'{"="*60}')
    print(f'{yr}年年报 ({doc.page_count}页)')

    # Find BS page (综合财务状况表)
    for pg in range(60, doc.page_count):
        text = doc[pg].get_text('text')
        if '综合财务状况表' in text and '人民币千元' in text and len(text) > 1000:
            # Dump key BS lines
            lines = text.split('\n')
            print(f'  BS p{pg+1}:')
            # Also check next page for continuation
            if pg+1 < doc.page_count:
                text += '\n' + doc[pg+1].get_text('text')
                lines = text.split('\n')
            for kw in ['贸易应收','现金及现金等价物','现金及银行','定期存款','贸易应付','合同负债','租赁负债','借款 ','资产总值','权益总额','本公司拥有人应佔權益','股本 ','總资产','總负债']:
                for i, l in enumerate(lines):
                    if kw in l and len(l.strip()) < 150:
                        ctx = ' | '.join(lines[max(0,i):min(len(lines),i+2)]).strip()
                        if len(ctx) < 250:
                            print(f'    {ctx[:200]}')
                        break
            break

    # Find CF page (综合现金流量表)
    for pg in range(60, doc.page_count):
        text = doc[pg].get_text('text')
        if '综合现金流量表' in text and '人民币千元' in text and len(text) > 800:
            lines = text.split('\n')
            print(f'  CF p{pg+1}:')
            for kw in ['经营所得现金','已付所得稅','已付利息','经营活动所得','购买物业','購置物業','购买固定','添置租赁','投资活动','已付股息','已付本公司','融资活动','租赁负债付款']:
                for i, l in enumerate(lines):
                    if kw in l and len(l.strip()) < 150:
                        ctx = ' | '.join(lines[max(0,i):min(len(lines),i+2)]).strip()
                        if len(ctx) < 250:
                            print(f'    {ctx[:200]}')
                        break
            break

    # Find dividend info (search for 股息 or 股利 or 末期股息)
    for pg in range(30, min(80, doc.page_count)):
        text = doc[pg].get_text('text')
        if '末期股息' in text or '末期股利' in text or ('股息' in text and '每股' in text and '人民币' in text):
            lines = text.split('\n')
            print(f'  分红 p{pg+1}:')
            for i, l in enumerate(lines):
                if any(kw in l for kw in ['末期股息','中期股息','每股股息','股息','股利','每股派','派息']):
                    ctx = ' | '.join(lines[max(0,i-1):min(len(lines),i+3)]).strip()
                    if len(ctx) < 200:
                        print(f'    {ctx[:200]}')
            break

    doc.close()
    print()
