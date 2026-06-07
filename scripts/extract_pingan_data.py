# -*- coding: utf-8 -*-
"""提取中国平安(601318) 2021-2025年报核心财务数据，输出溯源表用。"""
import fitz, sys, os, json, re
sys.stdout.reconfigure(encoding='utf-8')

BASE = r'd:\Project\investTemplate\07-分析输出\中国平安\年报'
YEARS = [2021, 2022, 2023, 2024, 2025]
FILES = {
    2021: '中国平安_601318_2021年年报_2022-03-17.pdf',
    2022: '中国平安_601318_2022年年报_2023-03-15.pdf',
    2023: '中国平安_601318_2023年年报_2024-03-21.pdf',
    2024: '中国平安_601318_2024年年报_2025-03-19.pdf',
    2025: '中国平安_601318_2025年年报_2026-03-26.pdf',
}

def find_page(doc, keyword, exclude_parent=True):
    """搜索关键词所在的页码（合并报表页）"""
    for pg in range(doc.page_count):
        text = doc[pg].get_text("text")
        if keyword in text:
            if exclude_parent and '母公司' in text[:500]:
                continue
            return pg + 1
    return None

def dump_page(doc, pg_num):
    """dump单页文本"""
    return doc[pg_num - 1].get_text("text")

def safe_float(s):
    """安全转float"""
    s = s.replace(',', '').replace(' ', '').replace('（', '').replace('）', '')
    try:
        return float(s)
    except:
        return None

def extract_bs_data(doc, pg, unit='million_yuan'):
    """从合并资产负债表提取关键数据"""
    text = dump_page(doc, pg)
    # 可能跨页，也看下一页
    if pg < doc.page_count:
        text += '\n' + dump_page(doc, pg + 1)

    data = {}
    # 找关键行
    lines = text.split('\n')

    # 资产总计
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if line_clean == '资产总计' or line_clean == '资产总計':
            # 找后面几行的数字
            for j in range(i, min(len(lines), i+5)):
                nums = re.findall(r'[\d,]+\.?\d*', lines[j])
                if len(nums) >= 1:
                    # 通常是最后一个大数
                    for n in reversed(nums):
                        v = safe_float(n)
                        if v and v > 100000:  # 万亿级
                            data['资产总计'] = v / 1e8  # 元→亿
                            break
                    if '资产总计' in data:
                        break

    # 负债合计
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if line_clean == '负债合计' or line_clean == '负债合計':
            for j in range(i, min(len(lines), i+5)):
                nums = re.findall(r'[\d,]+\.?\d*', lines[j])
                if len(nums) >= 1:
                    for n in reversed(nums):
                        v = safe_float(n)
                        if v and v > 100000:
                            data['负债合计'] = v / 1e8
                            break
                    if '负债合计' in data:
                        break

    # 所有者权益合计
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if line_clean in ['所有者权益合计', '所有者权益合計', '股东权益合计', '股東權益合計']:
            for j in range(i, min(len(lines), i+5)):
                nums = re.findall(r'[\d,]+\.?\d*', lines[j])
                if len(nums) >= 1:
                    for n in reversed(nums):
                        v = safe_float(n)
                        if v and v > 10000:
                            data['所有者权益合计'] = v / 1e8
                            break
                    if '所有者权益合计' in data:
                        break

    # 归母所有者权益
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if '归属于母公司' in line_clean and ('所有者权益' in line_clean or '股东权益' in line_clean):
            for j in range(i, min(len(lines), i+5)):
                nums = re.findall(r'[\d,]+\.?\d*', lines[j])
                if len(nums) >= 1:
                    for n in reversed(nums):
                        v = safe_float(n)
                        if v and v > 10000:
                            data['归母所有者权益'] = v / 1e8
                            break
                    if '归母所有者权益' in data:
                        break

    # 货币资金
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if line_clean in ['货币资金', '貨幣資金', '现金及存放中央银行款项']:
            for j in range(i, min(len(lines), i+3)):
                nums = re.findall(r'[\d,]+\.?\d*', lines[j])
                nums_big = [safe_float(n) for n in nums if safe_float(n) and safe_float(n) > 100]
                if nums_big:
                    data['货币资金'] = nums_big[0] / 1e8
                    break

    return data

def extract_pl_data(doc, pg):
    """从合并利润表提取关键数据"""
    text = dump_page(doc, pg)
    if pg < doc.page_count:
        text += '\n' + dump_page(doc, pg + 1)

    lines = text.split('\n')
    data = {}

    # 营业收入
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if line_clean in ['营业收入', '營業收入', '收入合计', '收入合計']:
            for j in range(i, min(len(lines), i+5)):
                nums = re.findall(r'[\d,]+\.?\d*', lines[j])
                for n in reversed(nums):
                    v = safe_float(n)
                    if v and v > 1000:
                        data['营业收入'] = v / 1e8
                        break
                if '营业收入' in data:
                    break

    # 净利润
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if line_clean == '净利润' or line_clean == '淨利潤':
            for j in range(i, min(len(lines), i+5)):
                nums = re.findall(r'[\d,]+\.?\d*', lines[j])
                for n in reversed(nums):
                    v = safe_float(n)
                    if v and v > 100:
                        data['净利润'] = v / 1e8
                        break
                if '净利润' in data:
                    break

    # 归母净利润
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if '归属于母公司' in line_clean and '净利润' in line_clean:
            for j in range(i, min(len(lines), i+5)):
                nums = re.findall(r'[\d,]+\.?\d*', lines[j])
                for n in reversed(nums):
                    v = safe_float(n)
                    if v and v > 100:
                        data['归母净利润'] = v / 1e8
                        break
                if '归母净利润' in data:
                    break

    return data

def extract_cf_data(doc, pg):
    """从合并现金流量表提取关键数据"""
    text = dump_page(doc, pg)
    if pg < doc.page_count:
        text += '\n' + dump_page(doc, pg + 1)
    if pg + 1 < doc.page_count:
        text += '\n' + dump_page(doc, pg + 2)

    lines = text.split('\n')
    data = {}

    # 经营活动现金流净额
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if '经营活动' in line_clean and '现金流量净额' in line_clean:
            for j in range(i, min(len(lines), i+3)):
                nums = re.findall(r'[\d,]+\.?\d*', lines[j])
                for n in reversed(nums):
                    v = safe_float(n)
                    if v and abs(v) > 100:
                        data['经营CF'] = v / 1e8
                        break
                if '经营CF' in data:
                    break

    # 投资活动现金流净额
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if '投资活动' in line_clean and '现金流量净额' in line_clean:
            for j in range(i, min(len(lines), i+3)):
                nums = re.findall(r'[\d,]+\.?\d*', lines[j])
                for n in reversed(nums):
                    v = safe_float(n)
                    if v and abs(v) > 10:
                        data['投资CF'] = v / 1e8
                        break
                if '投资CF' in data:
                    break

    # 筹资活动现金流净额
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if '筹资活动' in line_clean and '现金流量净额' in line_clean:
            for j in range(i, min(len(lines), i+3)):
                nums = re.findall(r'[\d,]+\.?\d*', lines[j])
                for n in reversed(nums):
                    v = safe_float(n)
                    if v and abs(v) > 10:
                        data['筹资CF'] = v / 1e8
                        break
                if '筹资CF' in data:
                    break

    # CAPEX: 购建固定资产、无形资产
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if '购建固定' in line_clean or '購建固定' in line_clean:
            for j in range(i, min(len(lines), i+3)):
                nums = re.findall(r'[\d,]+\.?\d*', lines[j])
                for n in reversed(nums):
                    v = safe_float(n)
                    if v and abs(v) > 1:
                        data['CAPEX'] = v / 1e8
                        break
                if 'CAPEX' in data:
                    break

    return data

def extract_summary_data(doc):
    """从年报前部摘要提取关键指标"""
    data = {}
    # 搜索 p5-p20 找每股股利、内含价值、偿付能力
    for pg in range(min(20, doc.page_count)):
        text = doc[pg].get_text("text")

        # 每股股利
        if '每股股利' in text or '每股股息' in text:
            for line in text.split('\n'):
                if ('每股股利' in line or '每股股息' in line) and '2.' in line:
                    nums = re.findall(r'[\d.]+', line)
                    for n in nums:
                        v = safe_float(n)
                        if v and 1 < v < 5:
                            data['每股股利'] = v
                            break
                    if '每股股利' in data:
                        break

        # 内含价值
        if '内含价值' in text and '亿元' in text:
            # 找"内含价值" + 数字 + 亿
            idx = text.find('内含价值')
            ctx = text[idx:idx+200]
            nums = re.findall(r'[\d,]+\.?\d*', ctx)
            for n in nums:
                v = safe_float(n)
                if v and 5000 < v < 20000:
                    data['内含价值'] = v
                    break

        # 偿付能力充足率
        if '综合偿付能力充足率' in text:
            idx = text.find('综合偿付能力充足率')
            ctx = text[idx:idx+150]
            nums = re.findall(r'(\d+\.?\d*)%', ctx)
            if nums:
                data['综合偿付能力充足率'] = safe_float(nums[0])

    return data

# ========================================
# Main extraction loop
# ========================================
all_data = {}

for year in YEARS:
    filepath = os.path.join(BASE, FILES[year])
    if not os.path.exists(filepath):
        print(f'{year}: FILE NOT FOUND')
        continue

    print(f'\n{"="*60}')
    print(f'Processing: {year}年年报')
    doc = fitz.open(filepath)

    bs_pg = find_page(doc, '合并资产负债表')
    pl_pg = find_page(doc, '合并利润表')
    cf_pg = find_page(doc, '合并现金流量表')

    print(f'  BS页: {bs_pg}, PL页: {pl_pg}, CF页: {cf_pg}')

    year_data = {'BS_pg': bs_pg, 'PL_pg': pl_pg, 'CF_pg': cf_pg}

    # 提取数据
    if bs_pg:
        year_data['BS'] = extract_bs_data(doc, bs_pg)
    if pl_pg:
        year_data['PL'] = extract_pl_data(doc, pl_pg)
    if cf_pg:
        year_data['CF'] = extract_cf_data(doc, cf_pg)

    year_data['Summary'] = extract_summary_data(doc)

    all_data[year] = year_data
    doc.close()

# 输出结果
print(f'\n{"="*60}')
print('EXTRACTION SUMMARY')
print(f'{"="*60}')

for year in sorted(all_data.keys()):
    d = all_data[year]
    print(f'\n--- {year}年 ---')
    print(f'  BS(p{d["BS_pg"]}): {d.get("BS", {})}')
    print(f'  PL(p{d["PL_pg"]}): {d.get("PL", {})}')
    print(f'  CF(p{d["CF_pg"]}): {d.get("CF", {})}')
    print(f'  Summary: {d.get("Summary", {})}')
