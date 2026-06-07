"""青岛港 - 全5年数据提取 + 生成溯源表骨架 (Markdown)"""
import fitz, os, sys, re

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

base = r"d:\Project\investTemplate\07-分析输出\青岛港年报"

# (path, bs_pages, pl_pages, cf_pages)
configs = {
    2025: ("青岛港：2025年度报告.pdf", [101,102], [105], [108,109]),
    2024: ("青岛港：2024年度报告.pdf", [113,114], [117], [120,121]),
    2023: ("青岛港：2023年度报告.pdf", [111,112], [115], [118,119]),
    2022: ("青岛港：2022年度报告.pdf", [116,117], [120], [123,124]),
    2021: ("青岛港：青岛港国际股份有限公司2021年年度报告.pdf", [101,102,103], [106,107], [111,112]),
}

def get_text(doc, pages):
    result = ""
    for p in pages:
        result += doc[p-1].get_text("text") + "\n"
    return result

def extract_value(lines, keyword, start_idx=0, exact=False):
    """在lines中搜索keyword后的大数字，返回(原值_yuan, 行内容)
    exact=True: 必须整行等于keyword（用于防止子串匹配）"""
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        if exact:
            if line != keyword:
                continue
        else:
            if keyword not in line:
                continue
        # 该行及后续几行中找大数字
        for j in range(i, min(i+8, len(lines))):
            nums = re.findall(r'[\d,]+\.?\d+', lines[j].strip())
            for n in nums:
                v = float(n.replace(',', ''))
                if v > 1000:
                    return v, line[:120]
        # 如果找不到大数字，返回该行
        return None, line[:120]
    return None, None

def extract_value_nosubstr(lines, keyword, exclude_substrs, start_idx=0):
    """搜索keyword但排除包含exclude_substrs中任一子串的行"""
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        if keyword not in line:
            continue
        # 检查是否需要排除
        excluded = False
        for es in exclude_substrs:
            if es in line:
                excluded = True
                break
        if excluded:
            continue
        for j in range(i, min(i+8, len(lines))):
            nums = re.findall(r'[\d,]+\.?\d+', lines[j].strip())
            for n in nums:
                v = float(n.replace(',', ''))
                if v > 1000:
                    return v, line[:120]
        return None, line[:120]
    return None, None

def extract_two_values(lines, keyword, start_idx=0):
    """提取两个连续的大数字（本年，上年）"""
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        if keyword in line:
            vals = []
            for j in range(i, min(i+8, len(lines))):
                nums = re.findall(r'[\d,]+\.?\d+', lines[j].strip())
                for n in nums:
                    v = float(n.replace(',', ''))
                    if v > 1000:
                        vals.append(v)
            if len(vals) >= 2:
                return vals[0], vals[1], line[:120]
            elif len(vals) >= 1:
                return vals[0], None, line[:120]
    return None, None, None

def to_yi(val):
    """元 → 亿"""
    if val is None:
        return None
    return round(val / 100_000_000, 2)

all_data = {}

for year in sorted(configs.keys()):
    fname, bs_pgs, pl_pgs, cf_pgs = configs[year]
    path = os.path.join(base, fname)
    doc = fitz.open(path)

    bs_text = get_text(doc, bs_pgs)
    pl_text = get_text(doc, pl_pgs)
    cf_text = get_text(doc, cf_pgs)

    bs_lines = bs_text.split('\n')
    pl_lines = pl_text.split('\n')
    cf_lines = cf_text.split('\n')

    d = {}

    # === BS ===
    bs_map = {
        "货币资金": "貨幣資金" if year >= 2022 else "货币资金",
        "交易性金融资产": "交易性金融資產" if year >= 2022 else "交易性金融资产",
        "应收账款": "應收賬款" if year >= 2022 else "应收账款",
        "流动资产合计": "流動資產合計" if year >= 2022 else "流动资产合计",
        "长期股权投资": "長期股權投資" if year >= 2022 else "长期股权投资",
        "固定资产": "固定資產" if year >= 2022 else "固定资产",
        "在建工程": "在建工程",
        "使用权资产": "使用權資產" if year >= 2022 else "使用权资产",
        "无形资产": "無形資產" if year >= 2022 else "无形资产",
        "非流动资产合计": "非流動資產合計" if year >= 2022 else "非流动资产合计",
        "资产总计": "資產總計" if year >= 2022 else "资产总计",
        "短期借款": "短期借款",
        "应付账款": "應付賬款" if year >= 2022 else "应付账款",
        "一年内到期非流动负债": "一年內到期的非流動負債" if year >= 2022 else "一年内到期的非流动负债",
        "流动负债合计": "流動負債合計" if year >= 2022 else "流动负债合计",
        "长期借款": "長期借款" if year >= 2022 else "长期借款",
        "租赁负债": "租賃負債" if year >= 2022 else "租赁负债",
        "非流动负债合计": "非流動負債合計" if year >= 2022 else "非流动负债合计",
        "负债合计": "負債合計" if year >= 2022 else "负债合计",
        "股本": "股本",
        "资本公积": "資本公積" if year >= 2022 else "资本公积",
        "归母权益合计": "歸屬於母公司股東權益合計" if year >= 2022 else "归属于母公司股东权益合计",
        "少数股东权益": "少數股東權益" if year >= 2022 else "少数股东权益",
        "股东权益合计": "股東權益合計" if year >= 2022 else "股东权益合计",
    }

    d["BS"] = {}
    for name, kw in bs_map.items():
        # 负债合计/流动负债合计/非流动负债合计 需要精确防止子串匹配
        if name in ("负债合计", "流动负债合计", "非流动负债合计"):
            if name == "负债合计":
                exclude = ["流動負債合計", "流动负债合计", "非流動負債合計", "非流动负债合计"]
            elif name == "流动负债合计":
                exclude = ["非流动负债合计", "非流動負債合計"]
            else:  # 非流动负债合计
                exclude = []
            v, ctx = extract_value_nosubstr(bs_lines, kw, exclude)
        elif name == "资产总计":
            exclude = ["非流动资产合计", "非流動資產合計", "流动资产合计", "流動資產合計"]
            v, ctx = extract_value_nosubstr(bs_lines, kw, exclude)
        elif name == "归母权益合计":
            exclude = ["少数股东权益", "少數股東權益"]
            v, ctx = extract_value_nosubstr(bs_lines, kw, exclude)
        else:
            v, ctx = extract_value(bs_lines, kw)
        d["BS"][name] = {"yuan": v, "yi": to_yi(v), "ctx": ctx}

    # === PL ===
    pl_map = {
        "营业收入": "營業收入" if year >= 2022 else "营业收入",
        "营业成本": "營業成本" if year >= 2022 else "营业成本",
        "税金及附加": "稅金及附加" if year >= 2022 else "税金及附加",
        "销售费用": "銷售費用" if year >= 2022 else "销售费用",
        "管理费用": "管理費用" if year >= 2022 else "管理费用",
        "研发费用": "研發費用" if year >= 2022 else "研发费用",
        "财务费用": "財務費用" if year >= 2022 else "财务费用",
        "利息费用": "利息費用" if year >= 2022 else "利息费用",
        "利息收入": "利息收入",
        "投资收益": "投資收益" if year >= 2022 else "投资收益",
        "对联营合营投资收益": "對聯營企業和合營企業的投資收益" if year >= 2022 else "对合营企业和联营企业的投资收益",
        "营业利润": "營業利潤" if year >= 2022 else "营业利润",
        "利润总额": "利潤總額" if year >= 2022 else "利润总额",
        "所得税费用": "所得稅費用" if year >= 2022 else "所得税费用",
        "净利润": "淨利潤" if year >= 2022 else "净利润",
        "归母净利润": "歸屬於母公司股東的淨利潤" if year >= 2022 else "归属于母公司股东的净利润",
        "少数股东损益": "少數股東損益" if year >= 2022 else "少数股东损益",
    }

    d["PL"] = {}
    for name, kw in pl_map.items():
        # 净利润 vs 归母净利润 需要防子串
        if name == "净利润":
            exclude = ["归属于母公司", "歸屬於母公司", "少数股东", "少數股東"]
            v, ctx = extract_value_nosubstr(pl_lines, kw, exclude)
        elif name == "归母净利润":
            # 2021年度有可能用不同的表述
            v, ctx = extract_value(pl_lines, kw)
            if v is None and year == 2021:
                v, ctx = extract_value(pl_lines, "归属于母公司股东的净利润")
        elif name == "对联营合营投资收益":
            v, ctx = extract_value(pl_lines, kw)
            if v is None and year == 2021:
                v, ctx = extract_value(pl_lines, "对合营企业和联营企业的投资收益")
        else:
            v, ctx = extract_value(pl_lines, kw)
        d["PL"][name] = {"yuan": v, "yi": to_yi(v), "ctx": ctx}

    # === CF ===
    cf_map = {
        "经营现金流净额": "經營活動產生的現金流量淨額" if year >= 2022 else "经营活动产生的现金流量净额",
        "CAPEX": "購建固定資產、無形資產和其他長期資產支付的現金" if year >= 2022 else "购建固定资产、无形资产和其他长期资产支付的现金",
        "投资现金流净额": "投資活動產生的現金流量淨額" if year >= 2022 else "投资活动产生的现金流量净额",
        "筹资现金流净额": "籌資活動產生的現金流量淨額" if year >= 2022 else "筹资活动产生的现金流量净额",
    }

    d["CF"] = {}
    for name, kw in cf_map.items():
        v, ctx = extract_value(cf_lines, kw)
        # fallback for 2021 simplified Chinese
        if v is None and year == 2021 and name == "CAPEX":
            v, ctx = extract_value(cf_lines, "购建固定资产、无形资产和其他长期资产支付的现金")
        d["CF"][name] = {"yuan": v, "yi": to_yi(v), "ctx": ctx}

    # === Additional Notes search ===
    # Search for restricted assets
    note_pages = list(range(150, min(250, doc.page_count)))
    restricted_found = False
    for pg in note_pages:
        text = doc[pg-1].get_text("text")
        if "受限" in text or "受到限制" in text or "抵押" in text or "质押" in text:
            idx = text.find("受限")
            if idx < 0: idx = text.find("受到限制")
            if idx < 0: idx = text.find("抵押")
            if idx < 0: idx = text.find("质押")
            if idx >= 0:
                d["NOTE_restricted"] = f"p{pg}: ...{text[max(0,idx-100):idx+300]}..."
                restricted_found = True
                break

    all_data[year] = d
    doc.close()

    # Print summary
    print(f"\n{'='*60}")
    print(f"📊 {year}年")
    print(f"  BS 资产总计: {d['BS']['资产总计']['yi']}亿")
    print(f"  BS 负债合计: {d['BS']['负债合计']['yi']}亿")
    print(f"  BS 归母权益: {d['BS']['归母权益合计']['yi']}亿")
    print(f"  PL 营业收入: {d['PL']['营业收入']['yi']}亿")
    print(f"  PL 归母净利: {d['PL']['归母净利润']['yi']}亿")
    print(f"  CF 经营CF:   {d['CF']['经营现金流净额']['yi']}亿")
    print(f"  CF CAPEX:    {d['CF']['CAPEX']['yi']}亿")

# Save JSON
import json
out_json = r"d:\Project\investTemplate\scripts\temp_qingdaogang_dumps\all_data.json"
# Convert to serializable
serializable = {}
for yr, data in all_data.items():
    serializable[str(yr)] = {}
    for section, items in data.items():
        if isinstance(items, dict):
            serializable[str(yr)][section] = {}
            for k, v in items.items():
                if isinstance(v, dict):
                    serializable[str(yr)][section][k] = {
                        "yi": v.get("yi"),
                        "ctx": str(v.get("ctx", ""))[:100]
                    }
                else:
                    serializable[str(yr)][section][k] = str(v)[:200]
        else:
            serializable[str(yr)][section] = str(items)[:200]

with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(serializable, f, ensure_ascii=False, indent=2, default=str)
print(f"\n✅ JSON保存到: {out_json}")
