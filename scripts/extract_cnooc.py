# -*- coding: utf-8 -*-
"""中海油 600938 五年年报核心数据批量提取"""
import fitz, os, json, re

BASE = r'd:\Project\investTemplate\07-分析输出\中海油'

FILES = {
    2025: '中海油_2025年报_A股.pdf',
    2024: '中海油_2024年报_A股.pdf',
    2023: '中海油_2023年报_A股.pdf',
    2022: '中海油_2022年报_A股.pdf',
    2021: '中海油_2021年报.pdf',
}

def find_statement_pages(doc, year):
    """Locate BS/PL/CF pages in a PDF"""
    result = {'bs': None, 'pl': None, 'cf': None, 'summary': None}

    # A-share keyword sets (2022-2025)
    kw_bs_a = ['合并资产负债表', '合并及公司资产负债表']
    kw_pl_a = ['合并利润表', '合并综合收益表', '合并损益及其他综合收益表']
    kw_cf_a = ['合并现金流量表']
    kw_summary = ['主要会计数据', '財務摘要']

    # HK-style keywords (2021)
    kw_bs_hk = ['合併財務狀況表', '合并财务状况表']
    kw_pl_hk = ['合併損益及其他綜合收益表', '合并损益及其他综合收益表']
    kw_cf_hk = ['合併現金流量表', '合并现金流量表']

    for pg in range(doc.page_count):
        text = doc[pg].get_text('text')

        # BS
        if result['bs'] is None:
            for kw in kw_bs_a + kw_bs_hk:
                if kw in text and ('编制单位' in text[:300] or '所有金額均以人民幣' in text[:500]):
                    result['bs'] = pg + 1
                    break
                elif kw in text and ('母公司' not in text[:300] or '公司及合併' in text[:300]):
                    result['bs'] = pg + 1
                    break

        # PL
        if result['pl'] is None:
            for kw in kw_pl_a + kw_pl_hk:
                if kw in text:
                    # Ensure it's consolidated
                    if '母公司' not in text[:300] or '合併及公司' in text[:300]:
                        result['pl'] = pg + 1
                        break

        # CF
        if result['cf'] is None:
            for kw in kw_cf_a + kw_cf_hk:
                if kw in text:
                    if '母公司' not in text[:300]:
                        result['cf'] = pg + 1
                        break

        # Summary
        if result['summary'] is None:
            for kw in kw_summary:
                if kw in text and '母公司' not in text[:300]:
                    result['summary'] = pg + 1
                    break

    return result

def parse_number(text):
    """Extract numeric value from text, handling comma separators"""
    text = text.strip().replace(',', '').replace(' ', '')
    # Handle negative numbers in parentheses like (1,234)
    if text.startswith('(') and text.endswith(')'):
        return -float(text[1:-1])
    # Handle regular numbers
    try:
        return float(text)
    except:
        return None

def extract_bs_items(doc, bs_page):
    """Extract key BS items from a consolidated BS page"""
    text = doc[bs_page - 1].get_text('text')
    # Also read next page for continuation
    if bs_page < doc.page_count:
        text += '\n' + doc[bs_page].get_text('text')

    items = {}
    lines = text.split('\n')

    # Key BS items to find (with multiple name variants)
    targets = {
        '货币资金': ['货币资金', '貨幣資金', '现金及现金等价物', '現金及現金等價物'],
        '交易性金融资产': ['交易性金融资产', '交易性金融資產'],
        '应收账款': ['应收账款', '應收賬款', '应收款项'],
        '存货': ['存货', '存貨'],
        '流动资产合计': ['流动资产合计', '流動資產合計', '流动资产总计'],
        '非流动资产合计': ['非流动资产合计', '非流動資產合計', '非流动资产总计'],
        '资产总计': ['资产总计', '資產總計', '总资产', '總資產'],
        '短期借款': ['短期借款'],
        '应付账款': ['应付账款', '應付賬款'],
        '应交税费': ['应交税费', '應交稅費'],
        '一年内到期非流动负债': ['一年内到期的非流动负债', '一年內到期的非流動負債'],
        '流动负债合计': ['流动负债合计', '流動負債合計'],
        '长期借款': ['长期借款', '長期借款'],
        '应付债券': ['应付债券', '應付債券'],
        '租赁负债': ['租赁负债', '租賃負債'],
        '非流动负债合计': ['非流动负债合计', '非流動負債合計'],
        '负债合计': ['负债合计', '負債合計', '总负债'],
        '股本': ['股本'],
        '归母权益': ['归属于母公司股东权益合计', '歸屬於母公司股東權益', '归属于母公司所有者权益', '歸屬於公司股東的權益'],
        '少数股东权益': ['少数股东权益', '少數股東權益', '非控制性權益'],
        '权益合计': ['股东权益合计', '股東權益合計', '所有者权益合计', '權益合計'],
    }

    for key, names in targets.items():
        for name in names:
            for i, line in enumerate(lines):
                if name in line:
                    # Try to get the number after the item name
                    # A-share format: "货币资金  214,695  154,196"
                    # HK format: same concept
                    parts = line.strip().split()
                    # Find numeric values in the line
                    nums = []
                    for p in parts:
                        cleaned = p.strip().replace(',', '').replace('(','').replace(')','').replace('%','')
                        try:
                            v = float(cleaned)
                            if abs(v) > 0.001:
                                nums.append(v)
                        except:
                            pass
                    if nums:
                        # Usually the last number(s) are the values
                        # Take the first numeric value after the keyword
                        items[key] = nums
                        break

            if key in items:
                break

    return items

def extract_pl_items(doc, pl_page):
    """Extract key PL items"""
    text = doc[pl_page - 1].get_text('text')
    if pl_page < doc.page_count:
        text += '\n' + doc[pl_page].get_text('text')

    items = {}
    lines = text.split('\n')

    targets = {
        '营业收入': ['营业收入', '營業收入', '收入总计', '收入總計', '一、 营业收入'],
        '营业成本': ['营业成本', '營業成本'],
        '税金及附加': ['税金及附加', '稅金及附加', '税金'],
        '销售费用': ['销售费用', '銷售費用', '销售及管理费用'],
        '管理费用': ['管理费用', '管理費用'],
        '研发费用': ['研发费用', '研發費用'],
        '财务费用': ['财务费用', '財務費用', '财务（费用）收入'],
        '投资收益': ['投资收益', '投資收益', '投资（损失）收益'],
        '营业利润': ['营业利润', '營業利潤', '二、 营业利润'],
        '利润总额': ['利润总额', '利潤總額', '三、 利润总额', '稅前利潤', '税前利润'],
        '所得税费用': ['所得税费用', '所得稅費用', '所得税'],
        '净利润': ['净利润', '淨利潤', '四、 净利润', '年度利潤'],
        '归母净利润': ['归属于母公司股东的净利润', '歸屬於母公司股東的淨利潤', '歸屬於公司股東的利潤'],
        '少数股东损益': ['少数股东损益', '少數股東損益', '非控制性權益'],
    }

    for key, names in targets.items():
        for name in names:
            for i, line in enumerate(lines):
                if name in line:
                    parts = line.strip().split()
                    nums = []
                    for p in parts:
                        cleaned = p.strip().replace(',', '').replace('(','').replace(')','').replace('%','')
                        try:
                            v = float(cleaned)
                            if abs(v) > 0.001:
                                nums.append(v)
                        except:
                            pass
                    if nums:
                        items[key] = nums
                        break
            if key in items:
                break

    return items

def extract_cf_items(doc, cf_page):
    """Extract key CF items"""
    text = doc[cf_page - 1].get_text('text')
    if cf_page < doc.page_count:
        text += '\n' + doc[cf_page].get_text('text')

    items = {}
    lines = text.split('\n')

    targets = {
        '经营活动现金流净额': ['经营活动产生的现金流量净额', '經營活動流入的現金淨額', '经营活动产生的现金流量'],
        'CAPEX': ['购建固定资产、无形资产', '購建固定資產、無形資產', '购建物业、厂房及设备', '購建物業、廠房及設備',
                  '资本支出', '資本支出', '购建固定资产无形资产和其他长期资产支付的现金'],
        '投资活动现金流净额': ['投资活动产生的现金流量净额', '投資活動流出的現金淨額', '投资活动产生的现金流量'],
        '筹资活动现金流净额': ['筹资活动产生的现金流量净额', '籌資活動流入的現金淨額', '筹资活动产生的现金流量'],
        '现金净增加额': ['现金及现金等价物净增加额', '現金及現金等價物淨增加額', '汇率变动对现金影响'],
    }

    for key, names in targets.items():
        for name in names:
            for i, line in enumerate(lines):
                if name in line:
                    parts = line.strip().split()
                    nums = []
                    for p in parts:
                        cleaned = p.strip().replace(',', '').replace('(','').replace(')','').replace('%','')
                        try:
                            v = float(cleaned)
                            if abs(v) > 0.001:
                                nums.append(v)
                        except:
                            pass
                    if nums:
                        items[key] = nums
                        break
            if key in items:
                break

    return items

def extract_summary(doc, summary_page):
    """Extract financial summary data (revenue, net profit, OCF, net assets, total assets)"""
    text = doc[summary_page - 1].get_text('text')
    if summary_page < doc.page_count:
        text += '\n' + doc[summary_page].get_text('text')

    items = {}
    lines = text.split('\n')

    # Look for key data points with their values
    targets = {
        '营业收入': ['营业收入'],
        '归母净利润': ['归属于母公司股东的净利润', '归属于上市公司股东的净利润'],
        '经营现金流': ['经营活动产生的现金流量净额'],
        '归母净资产': ['归属于母公司股东的净资产', '归属于上市公司股东的净资产'],
        '总资产': ['总资产'],
    }

    for key, names in targets.items():
        for name in names:
            for i, line in enumerate(lines):
                if name in line:
                    # Get next few lines for numeric values
                    context_lines = lines[i:i+4]
                    nums = []
                    for cl in context_lines:
                        parts = cl.strip().split()
                        for p in parts:
                            cleaned = p.strip().replace(',', '').replace('(','').replace(')','').replace('%','')
                            try:
                                v = float(cleaned)
                                if 100 < abs(v) < 100000000:
                                    nums.append(v)
                            except:
                                pass
                    if nums:
                        items[key] = nums
                        break
            if key in items:
                break

    return items

# Main extraction
all_data = {}

for year, fname in sorted(FILES.items()):
    path = os.path.join(BASE, fname)
    print(f'\nProcessing {year}: {fname}')
    doc = fitz.open(path)
    print(f'  Pages: {doc.page_count}')

    pages = find_statement_pages(doc, year)
    print(f'  Located: BS={pages["bs"]}, PL={pages["pl"]}, CF={pages["cf"]}, Summary={pages["summary"]}')

    year_data = {'pages': pages, 'bs': {}, 'pl': {}, 'cf': {}, 'summary': {}}

    if pages['bs']:
        year_data['bs'] = extract_bs_items(doc, pages['bs'])
        print(f'  BS items: {list(year_data["bs"].keys())}')

    if pages['pl']:
        year_data['pl'] = extract_pl_items(doc, pages['pl'])
        print(f'  PL items: {list(year_data["pl"].keys())}')

    if pages['cf']:
        year_data['cf'] = extract_cf_items(doc, pages['cf'])
        print(f'  CF items: {list(year_data["cf"].keys())}')

    if pages['summary']:
        year_data['summary'] = extract_summary(doc, pages['summary'])
        print(f'  Summary items: {list(year_data["summary"].keys())}')

    all_data[str(year)] = year_data
    doc.close()

# Save raw data
out_path = os.path.join(BASE, '_extracted_data.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)

print(f'\nSaved to {out_path}')
