"""青岛港 - 5年核心财务数据自动提取到JSON"""
import fitz, os, json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

base = r"d:\Project\investTemplate\07-分析输出\青岛港年报"

years_config = {
    2025: ("青岛港：2025年度报告.pdf", [101,102], 105, [108,109], 56),
    2024: ("青岛港：2024年度报告.pdf", [113,114], 117, [120,121], 67),
    2023: ("青岛港：2023年度报告.pdf", [111,112], 115, [118,119], 66),
    2022: ("青岛港：2022年度报告.pdf", [116,117], 120, [123,124], 65),
    2021: ("青岛港：青岛港国际股份有限公司2021年年度报告.pdf", [101,102], 106, [111], 94),
}

def get_page_text(doc, pg_num):
    """获取页码文本（1-indexed）"""
    return doc[pg_num - 1].get_text("text")

def find_value_in_lines(text, keywords, unit="yuan"):
    """在文本中查找关键词后的数字"""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        for kw in keywords:
            if kw in line.strip():
                # 向后搜索数字
                for j in range(i, min(i+6, len(lines))):
                    nums = re.findall(r'[\d,]+\.?\d*', lines[j].strip())
                    # 过滤掉太小的数（可能是附注编号）
                    nums_clean = []
                    for n in nums:
                        val = float(n.replace(',', ''))
                        if val > 1000:  # 大于1000才可能是金额
                            nums_clean.append(val)
                    if nums_clean:
                        return nums_clean, lines[i].strip()[:120]
    return None, None

def extract_all_years():
    results = {}

    for year in sorted(years_config.keys()):
        fname, bs_pages, pl_page, cf_pages, note_start = years_config[year]
        path = os.path.join(base, fname)

        if not os.path.exists(path):
            print(f"❌ {year}: 文件不存在")
            continue

        doc = fitz.open(path)

        # 拼接所有相关页的文本
        bs_text = ""
        for p in bs_pages:
            bs_text += get_page_text(doc, p)

        pl_text = get_page_text(doc, pl_page)

        cf_text = ""
        for p in cf_pages:
            cf_text += get_page_text(doc, p)

        yr_data = {"year": year, "source_pdf": fname}

        # === BS 提取 ===
        # 合并所有BS文本行
        bs_lines = bs_text.split('\n')

        # 辅助函数：在bs文本中搜索科目
        def bs_val(keywords):
            for i, line in enumerate(bs_lines):
                for kw in keywords:
                    if kw == line.strip():
                        # 向右搜索（同一行或下一行）
                        for j in range(i, min(i+10, len(bs_lines))):
                            nums = re.findall(r'[\d,]+\.?\d+', bs_lines[j].strip())
                            clean = []
                            for n in nums:
                                v = float(n.replace(',', ''))
                                if v > 100:  # 过滤小数字（页码/行号）
                                    clean.append(v)
                            if len(clean) >= 1:
                                # 取第一个大数字
                                return clean
                # 也检查行开头匹配
                if line.strip().startswith(kw):
                    for j in range(i, min(i+10, len(bs_lines))):
                        nums = re.findall(r'[\d,]+\.?\d+', bs_lines[j].strip())
                        clean = [float(n.replace(',','')) for n in nums if float(n.replace(',','')) > 100]
                        if len(clean) >= 1:
                            return clean
            return None

        # 关键BS科目
        bs_items = {
            "货币资金": ["貨幣資金"],
            "应收账款": ["應收賬款"],
            "流动资产合计": ["流動資產合計"],
            "长期股权投资": ["長期股權投資"],
            "固定资产": ["固定資產"],
            "在建工程": ["在建工程"],
            "无形资产": ["無形資產"],
            "非流动资产合计": ["非流動資產合計"],
            "资产总计": ["資產總計"],
            "短期借款": ["短期借款"],
            "应付账款": ["應付賬款"],
            "流动负债合计": ["流動負債合計"],
            "长期借款": ["長期借款"],
            "租赁负债": ["租賃負債"],
            "非流动负债合计": ["非流動負債合計"],
            "负债合计": ["負債合計"],
            "股本": ["股本"],
            "资本公积": ["資本公積"],
            "归母股东权益合计": ["歸屬於母公司股東權益合計"],
            "少数股东权益": ["少數股東權益"],
            "股东权益合计": ["股東權益合計"],
        }

        yr_data["BS"] = {}
        for name, kw_list in bs_items.items():
            vals = bs_val(kw_list)
            if vals:
                # BS 通常有两列（本年，上年），取第一个（本年末）
                yr_data["BS"][name] = vals[0] if len(vals) >= 1 else vals[0]

        # === PL 提取 ===
        pl_lines = pl_text.split('\n')

        def pl_val(keywords):
            for i, line in enumerate(pl_lines):
                for kw in keywords:
                    if kw == line.strip() or line.strip().startswith(kw):
                        for j in range(i, min(i+8, len(pl_lines))):
                            nums = re.findall(r'[\d,]+\.?\d+', pl_lines[j].strip())
                            clean = [float(n.replace(',','')) for n in nums if float(n.replace(',','')) > 100]
                            if len(clean) >= 1:
                                return clean, line.strip()[:120]
            return None, None

        pl_items = {
            "营业收入": ["營業收入"],
            "营业成本": ["營業成本"],
            "税金及附加": ["稅金及附加"],
            "销售费用": ["銷售費用"],
            "管理费用": ["管理費用"],
            "研发费用": ["研發費用"],
            "财务费用": ["財務費用"],
            "利息费用": ["利息費用"],
            "利息收入": ["利息收入"],
            "投资收益": ["投資收益"],
            "对联营合营投资收益": ["對聯營企業和合營企業的投資收益"],
            "营业利润": ["營業利潤"],
            "利润总额": ["利潤總額"],
            "所得税费用": ["所得稅費用"],
            "净利润": ["淨利潤"],
            "归母净利润": ["歸屬於母公司股東的淨利潤"],
            "少数股东损益": ["少數股東損益"],
        }

        yr_data["PL"] = {}
        for name, kw_list in pl_items.items():
            vals, _ = pl_val(kw_list)
            if vals:
                yr_data["PL"][name] = abs(vals[0]) if len(vals) >= 1 else abs(vals[0])

        # === CF 提取 ===
        cf_lines = cf_text.split('\n')

        def cf_val(keywords):
            for i, line in enumerate(cf_lines):
                for kw in keywords:
                    if kw in line.strip():
                        for j in range(i, min(i+6, len(cf_lines))):
                            nums = re.findall(r'[\d,]+\.?\d+', cf_lines[j].strip())
                            clean = [float(n.replace(',','')) for n in nums if float(n.replace(',','')) > 100]
                            if len(clean) >= 1:
                                return clean, line.strip()[:120]
            return None, None

        cf_items = {
            "经营现金流净额": ["經營活動產生的現金流量淨額"],
            "CAPEX": ["購建固定資產、無形資產和其他長期資產支付的現金"],
            "投资现金流净额": ["投資活動產生的現金流量淨額"],
            "筹资现金流净额": ["籌資活動產生的現金流量淨額"],
            "现金净增加额": ["現金淨增加額"],
        }

        yr_data["CF"] = {}
        for name, kw_list in cf_items.items():
            vals, _ = cf_val(kw_list)
            if vals:
                yr_data["CF"][name] = vals[0] if len(vals) >= 1 else vals[0]

        # 计算衍生值
        # 单位换算: 元→亿元
        div = 100_000_000

        print(f"\n{'='*60}")
        print(f"📊 {year}年 (来源: {fname})")
        print(f"  BS资产总计: {yr_data['BS'].get('资产总计', 'N/A')}")
        print(f"  PL营业收入: {yr_data['PL'].get('营业收入', 'N/A')}")
        print(f"  PL归母净利: {yr_data['PL'].get('归母净利润', 'N/A')}")
        print(f"  CF经营CF:  {yr_data['CF'].get('经营现金流净额', 'N/A')}")
        print(f"  CF CAPEX:   {yr_data['CF'].get('CAPEX', 'N/A')}")

        results[year] = yr_data
        doc.close()

    # 保存为JSON
    out_path = r"d:\Project\investTemplate\scripts\temp_qingdaogang_dumps\extracted.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON保存到: {out_path}")
    return results

results = extract_all_years()
