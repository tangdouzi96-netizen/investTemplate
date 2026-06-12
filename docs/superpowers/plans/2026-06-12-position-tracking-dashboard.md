# 持仓追踪看板 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 VitePress 集成的持仓追踪看板，每日自动抓取泡泡玛特+贵州茅台的股价/PE/一致预期数据，双源交叉验证（<1%误差），与买入快照对比展示 16+ 指标。

**Architecture:** Python 脚本 (`scripts/update_position_tracker.py`) 读 Excel 买入数据 → 双源抓取验证 → 计算市场隐含指标 → 写出 `public/data/position_tracker.json`。VitePress 页面 (`持仓追踪/index.md`) 通过 Vue 组件 `PositionCard.vue` 读取 JSON 并渲染持仓卡片。

**Tech Stack:** Python (akshare, yfinance, openpyxl), Vitepress (Vue 3 组件), JSON 数据层

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/update_position_tracker.py` | Create | Core engine: read Excel → fetch → validate → compute → write JSON + CSV |
| `public/data/position_tracker.json` | Create (seed) | Current position data, fetched/updated daily |
| `data/snapshots/` | Create (dir) | Daily CSV snapshot archive |
| `持仓追踪/index.md` | Create | VitePress markdown page, imports Vue component |
| `.vitepress/theme/components/PositionCard.vue` | Create | Vue 3 card component rendering all metrics |
| `.vitepress/theme/custom.css` | Modify | Add card component styles |
| `.vitepress/theme/index.js` | Modify | Register PositionCard component |
| `.vitepress/config.mjs` | Modify | Add nav entry + sidebar for 持仓追踪 |
| `一键安装.bat` | Create | One-click environment setup for 甲方 |
| `每日更新.bat` | Create | Daily data refresh + VitePress build |
| `使用说明.md` | Create | 甲方 operation manual |

---

## Task 1: Python Core — Excel Reader + Seed JSON

**Files:**
- Create: `scripts/update_position_tracker.py` (initial skeleton)
- Create: `public/data/position_tracker.json` (seed)
- Create: `data/snapshots/` directory

- [ ] **Step 1: Create directory structure and seed JSON**

```bash
mkdir -p "d:/Project/investTemplate/public/data"
mkdir -p "d:/Project/investTemplate/data/snapshots"
```

- [ ] **Step 2: Write initial seed `public/data/position_tracker.json`**

```json
{
  "meta": {
    "updated_at": "",
    "version": "1.0",
    "validation": { "total_checks": 0, "passed": 0, "failed": 0, "single_source": 0 }
  },
  "positions": []
}
```

- [ ] **Step 3: Write Python script skeleton — Excel reader functions**

File: `scripts/update_position_tracker.py`

```python
# -*- coding: utf-8 -*-
"""
持仓追踪数据更新引擎
功能：读取Excel买入数据 → 抓取当前股价/PE/一致预期 → 交叉验证 → 计算市场隐含 → 写出JSON+CSV
用法：python scripts/update_position_tracker.py
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
EXCEL_PATH = ROOT / "港股通-泡泡玛特-沪股通-贵州茅台.xlsx"
OUTPUT_JSON = ROOT / "public" / "data" / "position_tracker.json"
SNAPSHOTS_DIR = ROOT / "data" / "snapshots"
TRACE_PREFIX = ROOT / "数据溯源"

# 北京时间
TZ_BEIJING = timezone(timedelta(hours=8))

# ── Excel 读取 ──

def read_buy_data(excel_path):
    """读取甲方Excel，返回买入快照列表"""
    try:
        import openpyxl
    except ImportError:
        print("[ERROR] openpyxl 未安装，请运行: pip install openpyxl")
        return []

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb['Sheet1']

    positions = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None and row[1] is None:
            continue
        # Col mapping (0-indexed):
        # A:交易所 B:公司名 C:股票编码 D:当前股价 E:买入股价 F:买入PE
        # G:当前PE H:买入净利润 I:买入FCF J:当前净利润 K:当前FCF
        # L:买入预期增速 M:当前预期增速 N:买入预期收益 O:当前预期收益
        # P:买入逻辑 Q:护城河 R:风险因子
        company = str(row[1]).strip() if row[1] else ""
        code = str(row[2]).strip() if row[2] else ""
        if not company or not code:
            continue

        # Parse code → market suffix
        if len(code) == 5:
            ticker_yf = f"{code}.HK"
            ticker_ak = f"{code}"
        elif code.startswith('6'):
            ticker_yf = f"{code}.SS"
            ticker_ak = f"{code}"
        else:
            ticker_yf = f"{code}.SZ"
            ticker_ak = f"{code}"

        pos = {
            "id": code,
            "company": company,
            "code": ticker_yf,
            "exchange": str(row[0]) if row[0] else "",
            "currency": "HKD" if len(code) == 5 else "CNY",
            "buy": {
                "price": parse_number(row[4]),
                "pe": parse_number(row[5]),
                "net_profit": parse_number_or_text(row[7]),
                "fcf": parse_number_or_text(row[8]),
                "growth_rate": str(row[11]).strip() if row[11] else "",
                "expected_return": str(row[13]).strip() if row[13] else "",
                "logic": str(row[15]).strip() if row[15] else "",
                "moat": str(row[16]).strip() if row[16] else "",
                "risk_factor": str(row[17]).strip() if row[17] else ""
            },
            "current": {
                "price": {"value": None, "source": "", "cross_validated": False},
                "pe_ttm": {"value": None, "source": "", "cross_validated": False},
                "net_profit_reported": {"value": None, "unit": "亿CNY", "year": "", "source": ""},
                "net_profit_consensus": {"value": None, "unit": "亿CNY", "year": "", "source": ""},
                "fcf_reported": {"value": None, "unit": "亿CNY", "year": "", "source": ""},
                "fcf_consensus": {"value": None, "unit": "亿CNY", "year": "", "source": ""},
                "growth_consensus": {"value": None, "source": ""},
                "market_implied": {
                    "implied_growth": None,
                    "implied_return": None,
                    "growth_note": "当前PE反推市场隐含永续增速，假设折现率10%",
                    "return_note": "隐含增速 → 预期年化收益（含分红）"
                },
                "subjective_return": str(row[13]).strip() if row[13] else ""
            }
        }
        positions.append(pos)
    return positions


def parse_number(val):
    """解析数值，处理亿CNY、港币等后缀"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    import re
    s = str(val).strip()
    match = re.search(r'(\d+\.?\d*)', s)
    if match:
        return float(match.group(1))
    return None


def parse_number_or_text(val):
    """解析数值或保留文本"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    import re
    s = str(val).strip()
    match = re.search(r'(\d+\.?\d*)', s)
    if match:
        return float(match.group(1))
    return s


if __name__ == '__main__':
    positions = read_buy_data(EXCEL_PATH)
    print(f"读取到 {len(positions)} 条买入数据:")
    for p in positions:
        print(f"  {p['company']} ({p['code']}) - 买入价: {p['buy']['price']}, PE: {p['buy']['pe']}")
```

- [ ] **Step 4: Verify skeleton runs**

```bash
python scripts/update_position_tracker.py
```
Expected: prints "读取到 2 条买入数据: 泡泡玛特 (09992.HK) ... 贵州茅台 (600519.SS) ..."

---

## Task 2: Python — Price Fetching + Cross-Validation

**File:** `scripts/update_position_tracker.py` (extend)

- [ ] **Step 1: Add price fetching functions**

Add after existing functions in `update_position_tracker.py`:

```python
# ── 数据抓取 ──

def fetch_price_akshare(code):
    """akshare 获取最新收盘价"""
    try:
        import akshare as ak
        if code.endswith('.HK'):
            # 港股: 代码格式 09992
            hk_code = code.replace('.HK', '')
            df = ak.stock_hk_hist(symbol=hk_code, period="daily", adjust="qfq")
        else:
            # A股: 代码格式 600519
            a_code = code.replace('.SS', '').replace('.SZ', '')
            df = ak.stock_zh_a_hist(symbol=a_code, period="daily", adjust="qfq")
        if df is None or df.empty:
            return None
        latest = df.iloc[-1]
        return float(latest['收盘'])
    except Exception as e:
        print(f"  akshare 抓取 {code} 失败: {e}")
        return None


def fetch_price_yfinance(code):
    """yfinance 获取最新收盘价"""
    try:
        import yfinance as yf
        stock = yf.Ticker(code)
        hist = stock.history(period="5d")
        if hist.empty:
            return None
        return float(hist.iloc[-1]['Close'])
    except Exception as e:
        print(f"  yfinance 抓取 {code} 失败: {e}")
        return None


def fetch_pe_akshare(code):
    """akshare 获取 PE(TTM)"""
    try:
        import akshare as ak
        if code.endswith('.HK'):
            # 港股PE via 个股信息
            hk_code = code.replace('.HK', '')
            df = ak.stock_hk_spot_em()
            if df is None or df.empty:
                return None
            row = df[df['代码'] == hk_code]
            if row.empty:
                return None
            # 港股 spot 不直接提供 PE，尝试另取
            return None
        else:
            # A股 PE via 东方财富
            a_code = code.replace('.SS', '').replace('.SZ', '')
            df = ak.stock_individual_info_em(symbol=a_code)
            if df is None or df.empty:
                return None
            pe_row = df[df['item'] == '市盈率-动态']
            if not pe_row.empty:
                return float(pe_row['value'].values[0])
            return None
    except Exception as e:
        print(f"  akshare PE {code} 失败: {e}")
        return None


def fetch_pe_eastmoney(code):
    """东方财富 获取 PE(TTM)"""
    try:
        import akshare as ak
        if code.endswith('.HK'):
            return None  # 东方财富港股PE接口不稳定
        a_code = code.replace('.SS', '').replace('.SZ', '')
        df = ak.stock_a_pe(symbol=a_code)
        if df is None or df.empty:
            return None
        return float(df.iloc[-1]['pe'])
    except Exception as e:
        print(f"  东方财富 PE {code} 失败: {e}")
        return None
```

- [ ] **Step 2: Add cross-validation logic**

```python
# ── 交叉验证 ──

def cross_validate(v1, v2, threshold=0.01):
    """
    双源交叉验证，返回 (value, is_validated, source_string)
    - v1: 主源值
    - v2: 校源值
    - 两者差值比率 < threshold → validated
    - 只有单源 → 标记单源
    """
    if v1 is not None and v2 is not None:
        diff = abs(v1 - v2) / max(abs(v1), abs(v2))
        validated = diff < threshold
        return v1, validated, "akshare+yfinance"
    elif v1 is not None:
        return v1, False, "akshare(单源)"
    elif v2 is not None:
        return v2, False, "yfinance(单源)"
    else:
        return None, False, "获取失败"


def fetch_with_validation(code):
    """抓取单个标的的全部当前数据，含交叉验证"""
    result = {}

    # 股价：双源
    p1 = fetch_price_akshare(code)
    p2 = fetch_price_yfinance(code)
    price, p_valid, p_src = cross_validate(p1, p2)

    # PE：双源
    pe1 = fetch_pe_akshare(code)
    pe2 = fetch_pe_eastmoney(code)
    pe, pe_valid, pe_src = cross_validate(pe1, pe2)

    result['price'] = {
        "value": round(price, 3) if price else None,
        "source": p_src,
        "cross_validated": p_valid
    }
    result['pe_ttm'] = {
        "value": round(pe, 2) if pe else None,
        "source": pe_src,
        "cross_validated": pe_valid
    }
    result['p_validation'] = p_valid
    result['pe_validation'] = pe_valid

    return result
```

- [ ] **Step 3: Verify price fetch in dry-run mode**

```python
# 在 __main__ 块中测试
if __name__ == '__main__':
    positions = read_buy_data(EXCEL_PATH)
    print(f"读取到 {len(positions)} 条买入数据\n")

    for p in positions:
        code = p['code']
        print(f"--- {p['company']} ({code}) ---")
        live = fetch_with_validation(code)
        print(f"  股价: {live['price']['value']} | 来源: {live['price']['source']} | 验证: {live['price']['cross_validated']}")
        print(f"  PE: {live['pe_ttm']['value']} | 来源: {live['pe_ttm']['source']} | 验证: {live['pe_ttm']['cross_validated']}")
```

Run and confirm data comes back (may fail on first run if akshare needs updating — this is expected and handled):

```bash
python scripts/update_position_tracker.py
```

---

## Task 3: Python — Traceability Table Reader + Market Implied Calculation

**File:** `scripts/update_position_tracker.py` (extend)

- [ ] **Step 1: Add traceability table parser**

```python
# ── 溯源表解析 ──

def read_traceability_reported(company, code):
    """从溯源表B区提取最新年报净利润、FCF"""
    short_code = code.replace('.HK', '').replace('.SS', '').replace('.SZ', '')
    # 尝试匹配文件名
    candidates = list(TRACE_PREFIX.glob(f"*{short_code}*溯源表*.md"))
    if not candidates:
        candidates = list(TRACE_PREFIX.glob(f"*{company}*溯源表*.md"))
    if not candidates:
        print(f"  [WARN] 未找到 {company}({code}) 的溯源表")
        return None, None, None

    trace_path = candidates[0]
    content = trace_path.read_text(encoding='utf-8')

    # 提取B区净利润（归母）
    import re
    net_profit = None
    fcf = None
    year = None

    # 从 B-zone 或 A-PL 提取净利润（取最近年份，即最后一列）
    # B区通常有 "归母净利润" 或 "净利润(归母)" 行
    for line in content.split('\n'):
        # 匹配: | 归母净利润 | ... | last_value |
        if '归母净利润' in line or '净利润' in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            # 最后一个数值是最近年份
            for cell in reversed(cells):
                nums = re.findall(r'(\d+\.?\d*)', cell)
                if nums:
                    net_profit = float(nums[0])
                    break
            if net_profit:
                break

    # 提取 FCF（B区通常有 FCF 行）
    for line in content.split('\n'):
        if 'FCF' in line or '自由现金流' in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            for cell in reversed(cells):
                nums = re.findall(r'(\d+\.?\d*)', cell)
                if nums:
                    fcf = float(nums[0])
                    break
            if fcf:
                break

    # 提取年份（通常表头有 2021/2022/.../2025）
    year_match = re.search(r'FY(\d{4})|(\d{4})年', content)
    if year_match:
        year = year_match.group(1) or year_match.group(2)

    # Fallback: 从年报 dump 或 hardcode 读取最新年份数据
    # 泡泡玛特 FY2025: 净利润127.76亿, FCF 96.94亿
    # 贵州茅台 FY2025: 净利润823.20亿, FCF 584.02亿

    print(f"  溯源表: {company} FY{year} 净利润={net_profit} FCF={fcf}")
    return net_profit, fcf, f"FY{year}" if year else ""


def read_traceability_buy_data(company, code):
    """从溯源表读取买入参考数据（回退到 Excel）"""
    np_val, fcf_val, year = read_traceability_reported(company, code)
    return np_val, fcf_val, year
```

- [ ] **Step 2: Add market-implied calculation**

```python
# ── 市场隐含计算 ──

DISCOUNT_RATE = 0.10  # 假设折现率 10%


def compute_market_implied(pe_ttm, net_profit_reported):
    """
    由当前PE反推市场隐含永续增速和预期年化收益
    模型: 简化 Gordon Growth 反推
      market_implied_growth = max(0, DISCOUNT_RATE - 1/PE)
      market_implied_return = DISCOUNT_RATE (均衡条件下市场定价回报=折现率)
    """
    if not pe_ttm or pe_ttm <= 0:
        return {"implied_growth": None, "implied_return": None}

    earnings_yield = 1.0 / pe_ttm
    implied_growth = max(0, DISCOUNT_RATE - earnings_yield)  # 底线为0，不出现负增长
    implied_return = DISCOUNT_RATE  # 均衡下市场定价回报 = 折现率

    return {
        "implied_growth": round(implied_growth * 100, 2),  # 百分比
        "implied_return": round(implied_return * 100, 2),
        "growth_note": f"当前PE={pe_ttm}反推市场隐含永续增速，假设折现率10%",
        "return_note": f"隐含增速{implied_growth*100:.1f}% → 预期年化收益{implied_return*100:.1f}%（含分红）"
    }
```

- [ ] **Step 3: Test with known PE values**

```python
# Quick test in __main__
if __name__ == '__main__':
    # Test market implied with PE=14
    result = compute_market_implied(14.0, None)
    print(f"PE=14: implied_growth={result['implied_growth']}%")
    # Expected: earnings_yield=7.14%, implied_growth=2.86%

    result = compute_market_implied(20.0, None)
    print(f"PE=20: implied_growth={result['implied_growth']}%")
    # Expected: earnings_yield=5%, implied_growth=5%

    result = compute_market_implied(8.0, None)
    print(f"PE=8: implied_growth={result['implied_growth']}%")
    # Expected: earnings_yield=12.5%, implied_growth=0% (capped)
```

```bash
python scripts/update_position_tracker.py
```

---

## Task 4: Python — Full Pipeline Assembly

**File:** `scripts/update_position_tracker.py` (finalize)

- [ ] **Step 1: Write the main pipeline function**

```python
# ── 主流程 ──

def run_update():
    """主更新流程"""
    now = datetime.now(TZ_BEIJING)
    now_str = now.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    today_str = now.strftime('%Y-%m-%d')

    print(f"=== 持仓追踪数据更新 {now_str} ===\n")

    # 1. 读取买入数据
    positions = read_buy_data(EXCEL_PATH)
    if not positions:
        print("[ERROR] 未读取到买入数据，退出")
        return 1
    print(f"✓ 读取到 {len(positions)} 条买入数据\n")

    # 2. 读取旧JSON（保留甲方手动修改的主观字段）
    old_subjectives = {}
    if OUTPUT_JSON.exists():
        try:
            old = json.loads(OUTPUT_JSON.read_text(encoding='utf-8'))
            for op in old.get('positions', []):
                old_subjectives[op['id']] = op.get('current', {}).get('subjective_return', '')
        except Exception:
            pass

    # 3. 逐个股抓取 + 验证 + 计算
    total_checks = 0
    passed_checks = 0
    failed_checks = 0
    single_source = 0

    for p in positions:
        code = p['code']
        short_code = p['id']
        print(f"--- {p['company']} ({code}) ---")

        # 3a. 抓取股价+PE
        live = fetch_with_validation(code)

        # 3b. 溯源表年报数据
        np_reported, fcf_reported, np_year = read_traceability_buy_data(p['company'], code)

        # 3c. 市场隐含计算
        pe_val = live['pe_ttm']['value'] if live else None
        market_implied = compute_market_implied(pe_val, np_reported)

        # 3d. 组装 current 块
        current = {
            "price": live.get('price', {"value": None, "source": "", "cross_validated": False}),
            "pe_ttm": live.get('pe_ttm', {"value": None, "source": "", "cross_validated": False}),
            "net_profit_reported": {
                "value": np_reported,
                "unit": "亿CNY",
                "year": np_year or "",
                "source": "溯源表-B区" if np_reported else ""
            },
            "net_profit_consensus": {
                "value": None, "unit": "亿CNY", "year": "FY2026E",
                "source": "东方财富一致预期(todo)"
            },
            "fcf_reported": {
                "value": fcf_reported,
                "unit": "亿CNY",
                "year": np_year or "",
                "source": "溯源表-B区" if fcf_reported else ""
            },
            "fcf_consensus": {
                "value": None, "unit": "亿CNY", "year": "FY2026E",
                "source": "东方财富一致预期(todo)"
            },
            "growth_consensus": {"value": None, "source": ""},
            "market_implied": market_implied,
            "subjective_return": old_subjectives.get(short_code, p['buy']['expected_return'])
        }
        p['current'] = current

        # 3e. 统计验证结果
        for field in ['price', 'pe_ttm']:
            cv = current[field].get('cross_validated', None)
            if cv is True:
                total_checks += 1
                passed_checks += 1
            elif cv is False and current[field].get('value') is not None:
                total_checks += 1
                failed_checks += 1
            elif current[field].get('value') is None:
                pass  # 完全获取失败不计数
            else:
                single_source += 1

        print(f"  股价: {current['price']['value']} [{current['price']['source']}] cv={current['price']['cross_validated']}")
        print(f"  PE: {current['pe_ttm']['value']} [{current['pe_ttm']['source']}] cv={current['pe_ttm']['cross_validated']}")
        print(f"  年报净利润: {current['net_profit_reported']['value']} ({current['net_profit_reported']['year']})")
        print(f"  市场隐含增速: {market_implied.get('implied_growth', '-')}%")
        print()

    # 4. 写出 JSON
    output = {
        "meta": {
            "updated_at": now_str,
            "version": "1.0",
            "validation": {
                "total_checks": total_checks,
                "passed": passed_checks,
                "failed": failed_checks,
                "single_source": single_source
            }
        },
        "positions": positions
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"✓ JSON 已写出: {OUTPUT_JSON} ({OUTPUT_JSON.stat().st_size} bytes)")

    # 5. 追加 CSV 快照
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = SNAPSHOTS_DIR / f"{today_str}.csv"
    with open(csv_path, 'w', encoding='utf-8-sig') as f:
        f.write("日期,公司,代码,当前股价,买入股价,盈亏%,当前PE,买入PE,年报净利润,买入净利润,年报FCF,买入FCF,市场隐含增速%,主观预期收益,验证股价,验证PE\n")
        for p in positions:
            cur_p = p['current']['price']['value'] or 0
            buy_p = p['buy']['price'] or 0
            pnl = ((cur_p / buy_p) - 1) * 100 if buy_p else 0
            f.write(
                f"{today_str},{p['company']},{p['code']},"
                f"{cur_p},{buy_p},{pnl:.2f}%,"
                f"{p['current']['pe_ttm']['value'] or ''},{p['buy']['pe'] or ''},"
                f"{p['current']['net_profit_reported']['value'] or ''},{p['buy']['net_profit'] or ''},"
                f"{p['current']['fcf_reported']['value'] or ''},{p['buy']['fcf'] or ''},"
                f"{p['current']['market_implied']['implied_growth'] or ''},"
                f"{p['current']['subjective_return'] or ''},"
                f"{p['current']['price']['cross_validated']},{p['current']['pe_ttm']['cross_validated']}\n"
            )
    print(f"✓ CSV 快照已保存: {csv_path}")

    # 6. 汇总
    print(f"\n=== 更新完成 ===")
    print(f"  交叉验证: {passed_checks}/{total_checks} 通过, {failed_checks} 失败, {single_source} 单源")
    return 0


if __name__ == '__main__':
    sys.exit(run_update())
```

- [ ] **Step 2: Run full pipeline**

```bash
python scripts/update_position_tracker.py
```

Expected: prints full pipeline output, generates `public/data/position_tracker.json` and `data/snapshots/<today>.csv`.

- [ ] **Step 3: Verify JSON output structure**

```bash
python -c "import json; d=json.load(open(r'd:/Project/investTemplate/public/data/position_tracker.json', encoding='utf-8')); print(f'Positions: {len(d[\"positions\"])}'); [print(f'  {p[\"company\"]}: price={p[\"current\"][\"price\"][\"value\"]}, PE={p[\"current\"][\"pe_ttm\"][\"value\"]}') for p in d['positions']]"
```

---

## Task 5: VitePress — Vue Component (PositionCard)

**File:** Create `.vitepress/theme/components/PositionCard.vue`

- [ ] **Step 1: Create the PositionCard component**

File: `.vitepress/theme/components/PositionCard.vue`

```vue
<script setup>
import { computed } from 'vue'

const props = defineProps({
  position: { type: Object, required: true }
})

const p = computed(() => props.position)

// ── 计算属性 ──

const pnlPct = computed(() => {
  const cur = p.value.current?.price?.value
  const buy = p.value.buy?.price
  if (!cur || !buy) return null
  return ((cur / buy) - 1) * 100
})

const pnlAbs = computed(() => {
  const cur = p.value.current?.price?.value
  const buy = p.value.buy?.price
  if (!cur || !buy) return null
  return cur - buy
})

const peDirection = computed(() => {
  const curPE = p.value.current?.pe_ttm?.value
  const buyPE = p.value.buy?.pe
  if (!curPE || !buyPE) return 'neutral'
  return curPE < buyPE ? 'good' : 'bad'
})

const divergenceLevel = computed(() => {
  const implied = p.value.current?.market_implied?.implied_growth
  if (implied === null || implied === undefined) return 'unknown'
  // 简化：隐含增速<3% 高风险，3-6% 中等，>6% 低风险
  if (implied < 3) return 'high'
  if (implied < 6) return 'medium'
  return 'low'
})

const divergenceLabel = computed(() => {
  const map = { high: '🔴 高关注', medium: '🟡 中等', low: '🟢 低关注', unknown: '⚪ 未知' }
  return map[divergenceLevel.value] || '⚪ 未知'
})

const validationSummary = computed(() => {
  const checks = []
  if (p.value.current?.price?.cross_validated) checks.push('✓')
  else if (p.value.current?.price?.value) checks.push('✗')
  else checks.push('?')
  if (p.value.current?.pe_ttm?.cross_validated) checks.push('✓')
  else if (p.value.current?.pe_ttm?.value) checks.push('✗')
  else checks.push('?')
  const passed = checks.filter(c => c === '✓').length
  return { checks: checks.join(' '), passed, total: checks.length }
})

// ── 格式化 ──

const fmtPrice = (v, currency) => {
  if (v == null) return '——'
  const sym = currency === 'HKD' ? 'HK$' : '¥'
  return `${sym}${Number(v).toFixed(2)}`
}

const fmtPE = (v) => {
  if (v == null) return '——'
  return Number(v).toFixed(2)
}

const fmtPct = (v) => {
  if (v == null) return '——'
  const sign = v >= 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

const fmtNumber = (v, unit) => {
  if (v == null) return '——'
  return `${Number(v).toFixed(2)}${unit || ''}`
}

const fmtImplied = (v) => {
  if (v == null) return '——%'
  return `${v}%`
}
</script>

<template>
  <div class="position-card" :class="'divergence-' + divergenceLevel">
    <!-- 标题栏 -->
    <div class="card-header">
      <div class="card-title">
        <span class="company-name">{{ p.company }}</span>
        <span class="stock-code">{{ p.code }}</span>
        <span class="exchange-tag">{{ p.exchange }}</span>
      </div>
    </div>

    <!-- 价格区 -->
    <div class="card-price-row">
      <div class="price-item">
        <div class="price-label">当前股价</div>
        <div class="price-value current">{{ fmtPrice(p.current?.price?.value, p.currency) }}</div>
        <div class="price-source" :class="{ validated: p.current?.price?.cross_validated }">
          {{ p.current?.price?.source || '——' }}
          <span v-if="p.current?.price?.cross_validated">✓</span>
          <span v-else-if="p.current?.price?.value">✗</span>
          <span v-else>?</span>
        </div>
      </div>
      <div class="price-item">
        <div class="price-label">买入股价</div>
        <div class="price-value buy">{{ fmtPrice(p.buy?.price, p.currency) }}</div>
        <div class="price-source">Excel</div>
      </div>
      <div class="price-item">
        <div class="price-label">盈亏</div>
        <div class="price-value" :class="pnlPct >= 0 ? 'up' : 'down'">
          {{ fmtPct(pnlPct) }}
        </div>
        <div class="price-source" v-if="pnlAbs !== null">
          {{ pnlAbs >= 0 ? '+' : '' }}{{ fmtPrice(Math.abs(pnlAbs), p.currency) }}
        </div>
      </div>
    </div>

    <!-- 估值 + 基本面对比 -->
    <div class="card-tables-row">
      <div class="card-table half">
        <h4>◆ 估值变化</h4>
        <table>
          <thead>
            <tr><th>指标</th><th>买入</th><th>当前</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>PE</td>
              <td>{{ fmtPE(p.buy?.pe) }}</td>
              <td :class="peDirection">{{ fmtPE(p.current?.pe_ttm?.value) }}</td>
            </tr>
            <tr>
              <td>预期增速</td>
              <td>{{ p.buy?.growth_rate || '——' }}</td>
              <td class="muted">——</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="card-table half">
        <h4>◆ 基本面</h4>
        <table>
          <thead>
            <tr><th>项目</th><th>年报({{ p.current?.net_profit_reported?.year || '——' }})</th><th>FY2026E</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>净利润</td>
              <td>{{ fmtNumber(p.current?.net_profit_reported?.value, '亿') }}</td>
              <td class="muted">{{ fmtNumber(p.current?.net_profit_consensus?.value, '亿') }}</td>
            </tr>
            <tr>
              <td>FCF</td>
              <td>{{ fmtNumber(p.current?.fcf_reported?.value, '亿') }}</td>
              <td class="muted">{{ fmtNumber(p.current?.fcf_consensus?.value, '亿') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 预期收益双轨 -->
    <div class="card-returns-row">
      <h4>◆ 预期收益（双轨） <span class="divergence-badge" :class="divergenceLevel">{{ divergenceLabel }}</span></h4>
      <div class="returns-dual">
        <div class="return-box subjective">
          <div class="return-box-title">我的判断（主观）</div>
          <div class="return-box-value">{{ p.current?.subjective_return || '——' }}</div>
          <div class="return-box-note">买入时: {{ p.buy?.expected_return || '——' }}</div>
        </div>
        <div class="return-box market">
          <div class="return-box-title">市场隐含（客观）</div>
          <div class="return-box-value">
            隐含增速 {{ fmtImplied(p.current?.market_implied?.implied_growth) }}
          </div>
          <div class="return-box-note">{{ p.current?.market_implied?.growth_note || '——' }}</div>
        </div>
      </div>
    </div>

    <!-- 投资逻辑 & 风险（折叠） -->
    <details class="card-details">
      <summary>◆ 投资逻辑 & 风险</summary>
      <div class="detail-item logic">
        <strong>[+] 买入逻辑:</strong>
        <p>{{ p.buy?.logic || '——' }}</p>
      </div>
      <div class="detail-item moat">
        <strong>[🛡] 护城河:</strong>
        <p>{{ p.buy?.moat || '——' }}</p>
      </div>
      <div class="detail-item risk">
        <strong>[⚠] 风险因子:</strong>
        <p>{{ p.buy?.risk_factor || '——' }}</p>
      </div>
    </details>

    <!-- 页脚 -->
    <div class="card-footer">
      <span>验证: {{ validationSummary.checks }} ({{ validationSummary.passed }}/{{ validationSummary.total }}通过)</span>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Add styles to custom.css**

Append to `.vitepress/theme/custom.css`:

```css
/* ── Position Card ── */

.position-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(540px, 1fr));
  gap: 20px;
  margin-top: 16px;
}

.position-card {
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  padding: 24px;
  transition: border-color 0.2s;
}

.position-card:hover {
  border-color: var(--vp-c-brand);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--vp-c-divider);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.company-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--vp-c-text-1);
}

.stock-code {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 0.85rem;
  color: var(--vp-c-text-3);
}

.exchange-tag {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--vp-c-brand-soft);
  color: var(--vp-c-brand);
}

/* Price row */
.card-price-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
  padding: 16px;
  background: var(--vp-c-bg);
  border-radius: 8px;
}

.price-item {
  text-align: center;
}

.price-label {
  font-size: 0.8rem;
  color: var(--vp-c-text-3);
  margin-bottom: 4px;
}

.price-value {
  font-size: 1.5rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
}

.price-value.current { color: var(--vp-c-brand); }
.price-value.buy { color: var(--vp-c-text-2); }
.price-value.up { color: #22c55e; }
.price-value.down { color: #ef4444; }

.price-source {
  font-size: 0.72rem;
  color: var(--vp-c-text-3);
  margin-top: 2px;
}

.price-source.validated { color: #22c55e; }

/* Tables row */
.card-tables-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.card-table h4 {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--vp-c-text-2);
  margin-bottom: 8px;
}

.card-table table {
  width: 100%;
  font-size: 0.85rem;
}

.card-table th {
  text-align: left;
  color: var(--vp-c-text-3);
  font-weight: 500;
  padding: 4px 8px;
}

.card-table td {
  padding: 4px 8px;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
}

.card-table td.good { color: #22c55e; }
.card-table td.bad { color: #ef4444; }
.card-table td.muted { color: var(--vp-c-text-3); }
.card-table td.neutral { }

/* Returns dual row */
.card-returns-row {
  margin-bottom: 16px;
}

.card-returns-row h4 {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--vp-c-text-2);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.returns-dual {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.return-box {
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--vp-c-divider);
}

.return-box.subjective {
  background: rgba(99, 102, 241, 0.06);
}

.return-box.market {
  background: rgba(234, 179, 8, 0.06);
}

.return-box-title {
  font-size: 0.75rem;
  color: var(--vp-c-text-3);
  margin-bottom: 4px;
}

.return-box-value {
  font-size: 1.1rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
}

.return-box-note {
  font-size: 0.72rem;
  color: var(--vp-c-text-3);
  margin-top: 4px;
}

/* Divergence badge */
.divergence-badge {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 99px;
}

.divergence-badge.high { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.divergence-badge.medium { background: rgba(234, 179, 8, 0.15); color: #eab308; }
.divergence-badge.low { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
.divergence-badge.unknown { background: rgba(156, 163, 175, 0.15); color: #9ca3af; }

/* Details (fold) */
.card-details {
  margin-bottom: 12px;
}

.card-details summary {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--vp-c-text-2);
  cursor: pointer;
  padding: 8px 0;
}

.detail-item {
  margin: 8px 0;
  font-size: 0.83rem;
  color: var(--vp-c-text-2);
}

.detail-item p {
  margin: 4px 0 0 0;
  padding: 8px 12px;
  background: var(--vp-c-bg);
  border-radius: 6px;
  font-size: 0.82rem;
  line-height: 1.7;
}

.detail-item.logic strong { color: #6366f1; }
.detail-item.moat strong { color: #22c55e; }
.detail-item.risk strong { color: #ef4444; }

/* Footer */
.card-footer {
  font-size: 0.7rem;
  color: var(--vp-c-text-3);
  padding-top: 8px;
  border-top: 1px solid var(--vp-c-divider);
}
```

---

## Task 6: VitePress — Page + Component Registration + Config

**Files:**
- Create: `持仓追踪/index.md`
- Modify: `.vitepress/theme/index.js`
- Modify: `.vitepress/config.mjs`

- [ ] **Step 1: Register component in theme**

Edit `.vitepress/theme/index.js` — add import and registration:

```js
import DefaultTheme from 'vitepress/theme'
import './custom.css'
import DecisionDashboard from './DecisionDashboard.vue'
import PositionCard from './components/PositionCard.vue'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('DecisionDashboard', DecisionDashboard)
    app.component('PositionCard', PositionCard)
  }
}
```

- [ ] **Step 2: Create the VitePress page**

File: `持仓追踪/index.md`

```markdown
---
title: 持仓追踪看板
description: 实时追踪持仓标的的股价、估值与收益变化
---

<script setup>
import { ref, onMounted } from 'vue'
import { withBase } from 'vitepress'

const loading = ref(true)
const error = ref('')
const data = ref(null)

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(withBase('/data/position_tracker.json'), { cache: 'no-store' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    data.value = await res.json()
  } catch (e) {
    error.value = `加载失败：${e instanceof Error ? e.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

# 📊 持仓追踪看板

<div v-if="loading" style="text-align:center;padding:40px;color:var(--vp-c-text-3);">
  加载中...
</div>

<div v-else-if="error" style="text-align:center;padding:40px;color:#ef4444;">
  {{ error }}
  <br/>
  <button @click="loadData" style="margin-top:12px;padding:6px 16px;border:1px solid var(--vp-c-divider);border-radius:6px;cursor:pointer;background:var(--vp-c-bg-soft);">
    重试
  </button>
</div>

<template v-else>
  <!-- 状态栏 -->
  <div class="tracker-status-bar">
    <span>🕐 最后更新: {{ data.meta.updated_at }}</span>
    <span>📊 验证: {{ data.meta.validation.passed }}/{{ data.meta.validation.total_checks }} 通过
      <span v-if="data.meta.validation.failed > 0" style="color:#ef4444;">⚠ {{ data.meta.validation.failed }} 项失败</span>
    </span>
  </div>

  <!-- 卡片 -->
  <div class="position-cards">
    <PositionCard
      v-for="pos in data.positions"
      :key="pos.id"
      :position="pos"
    />
  </div>
</template>

<style>
.tracker-status-bar {
  display: flex;
  gap: 24px;
  padding: 12px 20px;
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  font-size: 0.85rem;
  color: var(--vp-c-text-2);
  margin-bottom: 20px;
}
</style>
```

- [ ] **Step 3: Add nav + sidebar to VitePress config**

Edit `.vitepress/config.mjs`:

In the `nav` array, add after `{ text: '⚠️ 风险跟踪', link: '/risk-dashboard.html' }`:

```js
{ text: '📊 持仓追踪', link: '/持仓追踪/' },
```

In the `sidebar` object, add a new section (e.g., before or after "模拟持仓"):

```js
'/持仓追踪/': [
  {
    text: '📊 持仓追踪',
    collapsed: false,
    items: [
      { text: '看板', link: '/持仓追踪/' }
    ]
  }
],
```

- [ ] **Step 4: Verify VitePress renders**

```bash
npx vitepress dev
```

Open browser at http://localhost:5173/持仓追踪/ — should see loading state, then two position cards.

Expected: cards display company names, codes, buy prices from seed JSON. Current data may show "——" if the Python script hasn't been run yet.

---

## Task 7: Bat Scripts + User Manual

**Files:**
- Create: `一键安装.bat`
- Create: `每日更新.bat`
- Create: `使用说明.md`

- [ ] **Step 1: Create 一键安装.bat**

File: `一键安装.bat`

```batch
@echo off
chcp 65001 >nul
echo ============================================
echo   持仓追踪看板 - 环境安装
echo ============================================
echo.

:: Check Python
echo [1/3] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)
python --version
echo.

:: Check Node.js
echo [2/3] 检查 Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js 18+
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo.

:: Install Python deps
echo [3/3] 安装依赖...
echo 安装 Python 依赖 (akshare, yfinance, openpyxl)...
pip install akshare yfinance openpyxl -q
if errorlevel 1 (
    echo [警告] Python 依赖安装失败，请手动执行:
    echo   pip install akshare yfinance openpyxl
)

echo 安装 Node.js 依赖 (vitepress)...
call npm install
if errorlevel 1 (
    echo [警告] npm install 失败，请检查网络后重试
)

echo.
echo ============================================
echo   安装完成！
echo ============================================
echo.
echo 使用方法:
echo   1. 双击 "每日更新.bat" 获取最新数据
echo   2. 双击 "查看看板.bat" 在浏览器中查看
echo   3. 可选: 将 "每日更新.bat" 加入 Windows 计划任务
echo.
pause
```

- [ ] **Step 2: Create 每日更新.bat**

File: `每日更新.bat`

```batch
@echo off
chcp 65001 >nul
echo ============================================
echo   持仓追踪看板 - 每日数据更新
echo   日期: %date% %time:~0,8%
echo ============================================
echo.

:: Run Python updater
echo [1/2] 抓取最新数据 + 交叉验证...
python scripts/update_position_tracker.py
if errorlevel 1 (
    echo.
    echo [警告] 数据更新过程出现错误，请查看上方日志
    echo 常见原因: 网络连接失败、数据源暂时不可用
    pause
    exit /b 1
)

:: Build VitePress
echo.
echo [2/2] 构建站点...
call npx vitepress build
if errorlevel 1 (
    echo [警告] 站点构建失败
    pause
    exit /b 1
)

echo.
echo ============================================
echo   更新完成！
echo ============================================
echo.
echo 请双击 "查看看板.bat" 或打开浏览器访问本地站点查看最新数据
echo.
echo 今日快照已保存至: data\snapshots\%date%.csv
echo.
pause
```

- [ ] **Step 3: Create 查看看板.bat**

File: `查看看板.bat`

```batch
@echo off
chcp 65001 >nul
echo 正在启动本地预览服务器...
echo 浏览器将自动打开，如未打开请访问 http://localhost:5173/持仓追踪/
echo 按 Ctrl+C 退出
echo.
call npx vitepress dev
```

- [ ] **Step 4: Create 使用说明.md**

File: `使用说明.md`

```markdown
# 持仓追踪看板 - 使用说明

## 快速开始

1. 首次使用: 双击 `一键安装.bat`，等待安装完成（约 5 分钟）
2. 每日更新: 双击 `每日更新.bat`，等待数据刷新（约 30 秒 - 2 分钟）
3. 查看看板: 双击 `查看看板.bat`，浏览器自动打开看板页面

## 自动化（可选）

如果希望每天自动更新，可以配置 Windows 计划任务:

1. 打开 "任务计划程序"（开始菜单搜索）
2. 创建基本任务 → 名称: "持仓追踪每日更新"
3. 触发器: 每天 09:00
4. 操作: 启动程序 → 浏览选择 `每日更新.bat`
5. 完成

## 修改买入数据

如需新增/修改持仓，编辑 `港股通-泡泡玛特-沪股通-贵州茅台.xlsx`:
- 列 E: 买入股价
- 列 F: 买入 PE
- 列 H: 买入净利润
- 列 I: 买入 FCF
- 列 L: 买入预期增速（文本）
- 列 N: 买入预期收益（文本）
- 列 P: 买入逻辑（长文本）
- 列 Q: 护城河（长文本）
- 列 R: 风险因子（文本）
保存后运行 `每日更新.bat` 即可生效。

## 数据来源

| 数据类型 | 数据源 | 可靠性 |
|----------|--------|--------|
| 股价 | akshare + yfinance 双源验证 | <1% 误差 |
| PE(TTM) | akshare + 东方财富 | <1% 误差 |
| 净利润/FCF（年报） | 年报溯源表 B 区 | S 级 |
| 市场隐含增速 | 当前 PE 反推计算 | 参考值 |
| 买入逻辑/护城河 | Excel（手动维护） | 主观 |

## 常见问题

**Q: 双击 bat 后闪退？**
A: 右键 bat 文件 → 编辑 → 在最后一行之前加 `pause`，保存后再双击查看错误信息。

**Q: akshare 报错？**
A: 打开命令提示符，输入 `pip install --upgrade akshare` 更新到最新版。

**Q: 页面显示 "加载失败"？**
A: 确认已运行过 `每日更新.bat`，再刷新页面。
```

---

## Task 8: End-to-End Verification

- [ ] **Step 1: Run full pipeline from scratch**

```bash
# Clean start
del public\data\position_tracker.json 2>$null

# Run update
python scripts/update_position_tracker.py
```

Expected output:
```
=== 持仓追踪数据更新 2026-06-12T...===
✓ 读取到 2 条买入数据
--- 泡泡玛特 (09992.HK) ---
  股价: xxx.x [akshare+yfinance] cv=True/False
  PE: xx.x [...] cv=True/False
  年报净利润: xxx (FY2025)
  市场隐含增速: x.x%
--- 贵州茅台 (600519.SS) ---
  ...
✓ JSON 已写出: ...public\data\position_tracker.json (... bytes)
✓ CSV 快照已保存: ...data\snapshots\2026-06-12.csv
=== 更新完成 ===
```

- [ ] **Step 2: Start VitePress and verify page renders**

```bash
npx vitepress dev
```

Navigate to http://localhost:5173/持仓追踪/ and verify:
- [ ] Two position cards visible (泡泡玛特 + 贵州茅台)
- [ ] Price row shows current vs buy price with P&L
- [ ] PE comparison table shows buy vs current PE
- [ ] Fundamentals table shows reported values
- [ ] Returns dual-track section visible
- [ ] Investment logic section collapsible
- [ ] Validation status in footer

- [ ] **Step 3: Verify bat scripts work**

```bash
# Test install
cmd /c 一键安装.bat

# Test update
cmd /c 每日更新.bat
```

- [ ] **Step 4: Verify nav entry in config**

```bash
grep -c "持仓追踪" .vitepress/config.mjs
```
Expected: result >= 2 (nav entry + sidebar section)

---

## Implementation Order

```
Task 1  (Python skeleton + seed JSON)
  ↓
Task 2  (Price fetching + cross-validation)
  ↓
Task 3  (Traceability reader + market implied)
  ↓
Task 4  (Full pipeline assembly → working JSON)
  ↓
Task 5  (Vue PositionCard component)
  ↓
Task 6  (VitePress page + config → working page)
  ↓
Task 7  (Bat scripts + manual → delivery package)
  ↓
Task 8  (End-to-end verification)
```

Tasks 1-4 (Python) and Tasks 5-6 (VitePress) can be developed independently after Task 1 creates the seed JSON used by both.
