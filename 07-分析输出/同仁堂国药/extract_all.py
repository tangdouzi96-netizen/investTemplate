import fitz, re, json, sys, glob
sys.stdout.reconfigure(encoding='utf-8')

BASE = "D:/Project/investTemplate/07-分析输出/同仁堂国药/年报"

def find_fs_pages(doc):
    pages = {'pl': [], 'bs': [], 'cf': [], 'summary': None}
    for pg in range(doc.page_count):
        text = doc[pg-1].get_text('text')
        # P&L
        if pg >= 40 and 'CONSOLIDATED STATEMENT OF PROFIT OR LOSS' in text:
            if pg+1 not in pages['pl']:
                pages['pl'].append(pg+1)
        # BS
        if pg >= 40 and 'CONSOLIDATED STATEMENT OF FINANCIAL POSITION' in text:
            if pg+1 not in pages['bs']:
                pages['bs'].append(pg+1)
        # CF
        if pg >= 40 and 'CONSOLIDATED STATEMENT OF CASH FLOWS' in text:
            if pg+1 not in pages['cf']:
                pages['cf'].append(pg+1)
        # Summary
        if pages['summary'] is None and 'FINANCIAL HIGHLIGHTS' in text:
            if 'ten financial years' in text.lower() or 'ten years' in text.lower():
                pages['summary'] = pg+1
                continue
            if 'Total assets' in text and 'Revenue' in text and 'Gross profit' in text:
                pages['summary'] = pg+1

    return pages

def extract_summary_table(doc, pg_num):
    """从财务摘要页提取10年数据"""
    text = doc[pg_num-1].get_text('text')
    lines = text.split('\n')

    # Find the data block - lines of pure numbers after HK$'000 header
    numeric_blocks = []
    current_block = []
    in_data = False

    for line in lines:
        ls = line.strip()
        # Check if this line is a pure number (with possible commas and decimals)
        if re.match(r'^[\d,]+\.?\d*$', ls):
            val = float(ls.replace(',', ''))
            if 100 < val < 10_000_000:
                current_block.append(val)
                in_data = True
        else:
            if in_data and len(current_block) >= 5:
                numeric_blocks.append(current_block)
            current_block = []
            in_data = False
    if in_data and len(current_block) >= 5:
        numeric_blocks.append(current_block)

    # Map blocks to financial metrics
    # The summary page has: Revenue, Gross profit, Profit before tax, Profit for year,
    # Profit attributable to owners, EPS, DPS Final, DPS Special,
    # Non-current assets, Current assets, Total assets,
    # Non-current liabilities, Current liabilities, Total liabilities, Net assets,
    # then ratios: Gross margin, Net margin, Current ratio, ROE, ROA, Payout ratio

    metrics = ['revenue', 'gross_profit', 'profit_before_tax', 'profit_for_year',
               'profit_attributable', 'eps', 'dps_final', 'dps_special',
               'non_current_assets', 'current_assets', 'total_assets',
               'non_current_liabilities', 'current_liabilities', 'total_liabilities',
               'net_assets', 'gross_margin', 'net_margin', 'current_ratio',
               'roe', 'roa', 'payout_ratio']

    result = {}
    for i, block in enumerate(numeric_blocks):
        if i < len(metrics) and len(block) >= 5:
            # First 5 values are 2025, 2024, 2023, 2022, 2021
            metric_name = metrics[i]
            result[metric_name] = {
                '2025': block[0] if len(block) > 0 else None,
                '2024': block[1] if len(block) > 1 else None,
                '2023': block[2] if len(block) > 2 else None,
                '2022': block[3] if len(block) > 3 else None,
                '2021': block[4] if len(block) > 4 else None,
            }

    return result

def extract_pl_details(doc, pl_pages):
    """从损益表页提取详细科目"""
    all_lines = []
    for pg in pl_pages:
        if pg <= doc.page_count:
            text = doc[pg-1].get_text('text')
            for i, line in enumerate(text.split('\n')):
                all_lines.append((pg, line.strip()))

    items = {}
    # Search for specific科目
    targets = {
        'revenue': ['Revenue'],
        'cost_of_sales': ['Cost of sales'],
        'gross_profit': ['Gross profit'],
        'other_income': ['Other income', 'Other revenue', 'Other gains'],
        'selling_expenses': ['Selling and distribution', 'Selling expenses'],
        'admin_expenses': ['Administrative expenses'],
        'other_expenses': ['Other expenses', 'Other operating expenses'],
        'finance_costs': ['Finance costs'],
        'profit_before_tax': ['Profit before income tax', 'Profit before tax'],
        'income_tax': ['Income tax expense'],
        'profit_for_year': ['Profit for the year'],
        'attributable_owners': ['attributable to owners', 'Owners of the Company'],
        'eps_basic': ['Basic', 'earnings per share'],
    }

    for key, kws in targets.items():
        for pg, line in all_lines:
            for kw in kws:
                if kw.lower() in line.lower():
                    # Find the last number on this line
                    nums = re.findall(r'[\d,]+\.?\d*', line)
                    if nums:
                        clean = nums[-1].replace(',', '')
                        items[key] = {'page': pg, 'value': clean, 'line': line[:120]}
                    break
            if key in items:
                break

    return items

def extract_bs_details(doc, bs_pages):
    """从财务状况表提取科目"""
    all_lines = []
    for pg in bs_pages:
        if pg <= doc.page_count:
            text = doc[pg-1].get_text('text')
            for i, line in enumerate(text.split('\n')):
                all_lines.append((pg, line.strip()))

    items = {}
    targets = {
        'ppe': ['Property, plant and equipment', 'plant and equipment'],
        'intangible': ['Intangible assets'],
        'right_of_use': ['Right-of-use assets'],
        'deferred_tax': ['Deferred tax assets'],
        'non_current_assets': ['Total non-current assets'],
        'inventories': ['Inventories'],
        'trade_receivables': ['Trade receivables', 'Trade and other receivables'],
        'cash': ['Cash and cash equivalents', 'Cash and bank balances'],
        'current_assets': ['Total current assets'],
        'total_assets': ['Total assets'],
        'trade_payables': ['Trade payables', 'Trade and other payables'],
        'lease_liabilities': ['Lease liabilities'],
        'current_liabilities': ['Total current liabilities'],
        'non_current_liabilities': ['Total non-current liabilities'],
        'total_liabilities': ['Total liabilities'],
        'total_equity': ['Total equity'],
        'share_capital': ['Share capital'],
        'retained_earnings': ['Retained earnings', 'Retained profits'],
    }

    for key, kws in targets.items():
        for pg, line in all_lines:
            for kw in kws:
                if kw.lower() in line.lower() and len(line) < 200:
                    nums = re.findall(r'[\d,]+\.?\d*', line)
                    if nums:
                        clean = nums[-1].replace(',', '')
                        # Validate the number is reasonable for千港元
                        try:
                            val = float(clean)
                            if 1 < val < 10_000_000:
                                items[key] = {'page': pg, 'value': clean, 'line': line[:120]}
                        except:
                            pass
                    break
            if key in items:
                break

    return items

def extract_cf_details(doc, cf_pages):
    """从现金流量表提取关键数据"""
    all_lines = []
    for pg in cf_pages:
        if pg <= doc.page_count:
            text = doc[pg-1].get_text('text')
            for i, line in enumerate(text.split('\n')):
                all_lines.append((pg, line.strip()))

    items = {}
    targets = {
        'operating_cf': ['Net cash flows from operating activities', 'Net cash generated from operating'],
        'capex': ['Purchase of property, plant and equipment', 'Purchase of items of property',
                  'Purchases of property, plant and equipment'],
        'investing_cf': ['Net cash flows from investing activities', 'Net cash used in investing'],
        'financing_cf': ['Net cash flows from financing activities', 'Net cash used in financing'],
        'dividend_paid': ['Dividends paid', 'Dividend paid'],
    }

    for key, kws in targets.items():
        for pg, line in all_lines:
            for kw in kws:
                if kw.lower() in line.lower() and len(line) < 200:
                    nums = re.findall(r'[\d,]+\.?\d*', line)
                    if nums:
                        clean = nums[-1].replace(',', '')
                        try:
                            val = float(clean)
                            if 100 < val < 10_000_000:
                                items[key] = {'page': pg, 'value': clean, 'line': line[:120]}
                        except:
                            pass
                    break
            if key in items:
                break

    return items

# Main
all_data = {}

for year in [2021, 2022, 2023, 2024, 2025]:
    files = glob.glob(f'{BASE}/同仁堂国药_03613_{year}年年报_*')
    if not files:
        continue

    doc = fitz.open(files[0])
    print(f'\n{"="*60}')
    print(f'{year} ({doc.page_count} pages)')

    pages = find_fs_pages(doc)
    print(f'  PL pages: {pages["pl"]}')
    print(f'  BS pages: {pages["bs"]}')
    print(f'  CF pages: {pages["cf"]}')
    print(f'  Summary: p{pages["summary"]}')

    year_data = {'pages': pages}

    # Extract summary
    if pages['summary']:
        summary = extract_summary_table(doc, pages['summary'])
        year_data['summary'] = summary
        if summary:
            rev = summary.get('revenue', {})
            print(f'  Revenue: 2025={rev.get("2025")} 2024={rev.get("2024")} 2023={rev.get("2023")}')

    # Extract PL details
    if pages['pl']:
        pl = extract_pl_details(doc, pages['pl'])
        year_data['pl'] = pl
        for k, v in pl.items():
            print(f'  PL {k}: {v["value"]} (p{v["page"]})')

    # Extract BS details
    if pages['bs']:
        bs = extract_bs_details(doc, pages['bs'])
        year_data['bs'] = bs
        for k, v in bs.items():
            print(f'  BS {k}: {v["value"]} (p{v["page"]})')

    # Extract CF details
    if pages['cf']:
        cf = extract_cf_details(doc, pages['cf'])
        year_data['cf'] = cf
        for k, v in cf.items():
            print(f'  CF {k}: {v["value"]} (p{v["page"]})')

    all_data[str(year)] = year_data
    doc.close()

with open('extracted_raw.json', 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)
print('\nDone -> extracted_raw.json')
