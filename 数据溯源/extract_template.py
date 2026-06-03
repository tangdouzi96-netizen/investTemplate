"""
数据溯源表标准化提取模板 V1.0
支持 A股 + 港股年报 PDF，自动定位报表页并提取核心科目
用法：修改 CONFIG 区参数后直接运行
"""
import fitz, re, json, sys, glob
sys.stdout.reconfigure(encoding='utf-8')

# ═══════════════════════════════════════════════════
# 市场差异速查
# ═══════════════════════════════════════════════════
#              A股                       港股
# 准则        中国企业会计准则           HKFRS (≈IFRS)
# 利润表      合并利润表                合并损益表 / 合并综合收益表
# 资产负债表  合并资产负债表            合并财务状况表
# 现金流量表  合并现金流量表            合并现金流量表
# 单位        元 或 万元                 千港元
# 报表标题    "合并资产负债表"           "CONSOLIDATED STATEMENT OF FINANCIAL POSITION"
# 研发费用    有单独科目                无（非药企）/药企有
# 财务费用    通常为净支出              净现金企业可能为净收益
# PL定位词    "一、营业总收入"          "Revenue" 或 "收入"
# BS合计陷阱  负债合计 vs 流动负债合计   英文没有"流动"/"非流动"前缀干扰（行尾匹配即可）
# 分红披露    末期+可能中期              末期+可能特别股息
# 科目跨行截断 购建固定资产...（常见）   Purchase of property, plant...（较少）
# ═══════════════════════════════════════════════════

# ═══════════════════════════════════════════════════
# CONFIG 区：按标的修改以下参数
# ═══════════════════════════════════════════════════
CONFIG = {
    "company_name": "示例公司",          # 公司名称
    "stock_code": "000000",             # 股票代码
    "market": "A",                      # "A" = A股, "HK" = 港股
    "pdf_folder": "年报",               # 年报 PDF 所在文件夹
    "years": [2021, 2022, 2023, 2024, 2025],
    "pdf_pattern": "{name}_{code}_{year}年年报*.pdf",  # 文件名匹配模式
    "unit": "万元" if "A" else "千港元",  # 年报单位
    "convert_to_yi": True,              # 是否转换为亿
    "output_path": "{name}_{code}_数据溯源表_自动提取.json",
}

# 港股特有：科目名映射（英文→中文）
HK_PL_MAP = {
    "revenue": ["Revenue", "收入"],
    "cost": ["Cost of sales", "銷售成本", "销售成本"],
    "gross_profit": ["Gross profit", "毛利"],
    "selling": ["Distribution and selling", "Selling and distribution", "分銷及銷售"],
    "admin": ["General and administrative", "Administrative expenses", "一般及行政"],
    "impairment": ["Net impairment", "減值", "减值"],
    "other_gains": ["Other gains", "Other income", "其他利得", "其他收入"],
    "finance_income": ["Finance income", "財務收益"],
    "finance_costs": ["Finance costs", "財務成本"],
    "pretax": ["Profit before income tax", "除所得稅"],
    "tax": ["Income tax", "所得稅"],
    "attrib_owners": ["Owners of the Company", "本公司擁有人"],
    "eps": ["Basic and diluted", "每股基本"],
}

HK_BS_MAP = {
    "ppe": ["Property, plant and equipment", "物業、廠房及設備"],
    "rou": ["Right-of-use assets", "使用權資產"],
    "intangible": ["Intangible assets", "無形資產"],
    "nca_total": ["Total non-current assets", "非流動資產合計"],
    "inventories": ["Inventories", "存貨"],
    "trade_recv": ["Trade receivables", "貿易應收款項"],
    "bank_dep": ["Short-term bank deposits", "短期銀行存款"],
    "cash": ["Cash and cash equivalents", "現金及現金等價物"],
    "ca_total": ["Total current assets", "流動資產合計"],
    "total_assets": ["Total assets", "總資產"],
    "borrowings": ["Borrowings", "借貸"],
    "lease_ncl": ["Lease liabilities", "租賃負債"],
    "ncl_total": ["Total non-current liabilities", "非流動負債合計"],
    "cl_total": ["Total current liabilities", "流動負債合計"],
    "total_liabilities": ["Total liabilities", "總負債"],
    "total_equity": ["Total equity", "權益總額"],
}

HK_CF_MAP = {
    "ocf": ["Net cash.*?operating activities", "經營活動.*?現金淨額"],
    "capex_ppe": ["Purchase of property, plant and equipment and intangible", "購買物業、廠房及設備"],
    "capex_prepay": ["Prepayment.*?property", "Deposit.*?property", "預付款.*?物業", "按金.*?物業"],
    "invest_cf": ["Net cash.*?investing activities", "投資活動.*?現金"],
    "finance_cf": ["Net cash.*?financing activities", "融資活動.*?現金"],
    "div_shareholders": ["Dividends paid to.*?shareholders", "已付.*?股東.*?股息"],
}


def find_statement_pages(doc, market="A"):
    """自动定位三大报表首页。返回 {pl, bs, cf} 页码（1-indexed）。"""
    pages = {"pl": None, "bs": None, "cf": None, "auditor": None, "summary": None}

    if market == "HK":
        pl_kw = "CONSOLIDATED STATEMENT OF PROFIT OR LOSS"
        bs_kw = "CONSOLIDATED STATEMENT OF FINANCIAL POSITION"
        cf_kw = "CONSOLIDATED STATEMENT OF CASH FLOWS"
        auditor_kw = "INDEPENDENT AUDITOR"
    else:  # A股
        pl_kw = "合并利润表"
        bs_kw = "合并资产负债表"
        cf_kw = "合并现金流量表"
        auditor_kw = "审计报告"

    for pg in range(doc.page_count):
        text = doc[pg].get_text("text")
        first200 = text[:200]

        if pages["auditor"] is None and auditor_kw in first200:
            pages["auditor"] = pg + 1

        if pages["pl"] is None and pl_kw in first200 and "母公司" not in first200:
            pages["pl"] = pg + 1

        if pages["bs"] is None and bs_kw in first200 and "母公司" not in first200:
            pages["bs"] = pg + 1

        if pages["cf"] is None and cf_kw in first200 and "母公司" not in first200:
            pages["cf"] = pg + 1

        if market == "HK" and pages["summary"] is None and "FINANCIAL HIGHLIGHTS" in text:
            if "ten years" in text.lower() or "十年" in text:
                pages["summary"] = pg + 1

    # 港股备选：如果标题页未找到，用"一、经营活动"定位CF
    if market == "HK" and pages["cf"] is None:
        for pg in range(doc.page_count):
            text = doc[pg].get_text("text")
            if "Cash generated from" in text and "operations" in text.lower():
                if "NOTES" not in text[:200]:
                    pages["cf"] = pg + 1
                    break

    return pages


def extract_number_from_context(lines, start_idx, min_val=100, max_val=99999999):
    """从文本行中提取满足条件的数值。返回 (当前年值, 上年度值)。"""
    nums = []
    for j in range(start_idx, min(len(lines), start_idx + 5)):
        found = re.findall(r'[\d,]+\.?\d*', lines[j].strip())
        for n in found:
            if n:
                try:
                    v = float(n.replace(',', ''))
                    if min_val < abs(v) < max_val:
                        nums.append(v)
                        if len(nums) >= 2:
                            return nums[0], nums[1]
                except:
                    pass
    if nums:
        return nums[0], None
    return None, None


def extract_from_report(doc, market="A"):
    """核心提取函数：从单份年报中提取所有科目。"""
    pages = find_statement_pages(doc, market)
    all_lines_pl = []
    all_lines_bs = []
    all_lines_cf = []

    # 读取三大报表页
    if pages["pl"]:
        for p in [pages["pl"], pages["pl"] + 1, pages["pl"] + 2]:
            if p <= doc.page_count:
                text = doc[p - 1].get_text("text")
                all_lines_pl.extend((p, l.strip()) for l in text.split('\n'))

    if pages["bs"]:
        for p in [pages["bs"], pages["bs"] + 1, pages["bs"] + 2]:
            if p <= doc.page_count:
                text = doc[p - 1].get_text("text")
                all_lines_bs.extend((p, l.strip()) for l in text.split('\n'))

    if pages["cf"]:
        for p in [pages["cf"], pages["cf"] + 1]:
            if p <= doc.page_count:
                text = doc[p - 1].get_text("text")
                all_lines_cf.extend((p, l.strip()) for l in text.split('\n'))

    result = {"pages": pages}

    # 提取 PL
    if market == "HK":
        pl_map = HK_PL_MAP
    else:
        pl_map = {}  # A股科目映射待扩展

    pl_data = {}
    for key, keywords in pl_map.items():
        for pg, line in all_lines_pl:
            for kw in keywords:
                if kw in line and len(line) < 200:
                    curr, prior = extract_number_from_context(
                        [l for _, l in all_lines_pl],
                        next(i for i, (_, l) in enumerate(all_lines_pl) if l == line),
                        100, 99999999
                    )
                    if curr:
                        pl_data[key] = {"current": curr, "prior": prior, "page": pg}
                    break
            if key in pl_data:
                break

    result["pl"] = pl_data

    # 提取 BS
    if market == "HK":
        bs_map = HK_BS_MAP
    else:
        bs_map = {}

    bs_data = {}
    for key, keywords in bs_map.items():
        for pg, line in all_lines_bs:
            for kw in keywords:
                if kw in line and len(line) < 200:
                    curr, prior = extract_number_from_context(
                        [l for _, l in all_lines_bs],
                        next(i for i, (_, l) in enumerate(all_lines_bs) if l == line),
                        1000, 99999999
                    )
                    if curr:
                        bs_data[key] = {"current": curr, "prior": prior, "page": pg}
                    break
            if key in bs_data:
                break

    result["bs"] = bs_data

    # 提取 CF
    if market == "HK":
        cf_map = HK_CF_MAP
    else:
        cf_map = {}

    cf_data = {}
    for key, keywords in cf_map.items():
        for pg, line in all_lines_cf:
            for kw in keywords:
                if re.search(kw, line, re.IGNORECASE) and len(line) < 200:
                    curr, prior = extract_number_from_context(
                        [l for _, l in all_lines_cf],
                        next(i for i, (_, l) in enumerate(all_lines_cf) if l == line),
                        100, 99999999
                    )
                    if curr:
                        cf_data[key] = {"current": curr, "prior": prior, "page": pg}
                    break
            if key in cf_data:
                break

    result["cf"] = cf_data

    return result


def run(config):
    """主入口：遍历所有年份，提取并保存。"""
    all_results = {}

    for year in config["years"]:
        pattern = config["pdf_pattern"].format(
            name=config["company_name"],
            code=config["stock_code"],
            year=year
        )
        files = glob.glob(f"{config['pdf_folder']}/{pattern}")
        if not files:
            print(f"⚠️ {year}: 未找到PDF文件")
            continue

        doc = fitz.open(files[0])
        print(f"\n📊 {year} ({doc.page_count}页) → {files[0].split('/')[-1][:60]}")

        data = extract_from_report(doc, config["market"])
        all_results[str(year)] = data

        # 简要输出
        for section, items in data.items():
            if section in ("pl", "bs", "cf"):
                print(f"  {section}: {len(items)} 科目")
        print(f"  报表页: PL=p{data['pages'].get('pl','?')} BS=p{data['pages'].get('bs','?')} CF=p{data['pages'].get('cf','?')}")

        doc.close()

    # 保存
    output = config["output_path"].format(
        name=config["company_name"],
        code=config["stock_code"]
    )
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已保存至 {output}")

    return all_results


# ═══════════════════════════════════════════════════
# 使用示例：取消下方注释并修改 CONFIG 后运行
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    print("数据溯源表标准化提取模板 V1.0")
    print("请修改 CONFIG 区参数后运行。")
    print("\n支持的科目：")
    print("  港股PL: " + ", ".join(HK_PL_MAP.keys()))
    print("  港股BS: " + ", ".join(HK_BS_MAP.keys()))
    print("  港股CF: " + ", ".join(HK_CF_MAP.keys()))

    # 示例：取消注释运行
    # CONFIG["company_name"] = "同仁堂国药"
    # CONFIG["stock_code"] = "03613"
    # CONFIG["market"] = "HK"
    # CONFIG["pdf_folder"] = "D:/Project/investTemplate/07-分析输出/同仁堂国药/年报"
    # run(CONFIG)
