# 持仓追踪看板 — 设计文档

> 版本 1.0 | 2026-06-12 | 乙方交付物设计

---

## 1. 背景与目标

### 需求起源

用户（乙方）需交付一个投资持仓追踪看板给甲方。甲方持有泡泡玛特（09992.HK，港股通）和贵州茅台（600519.SH，沪股通），需要每日追踪 16 项指标，对比"买入时"与"当前"的变化，辅助持有期决策。

### 核心指标（16 项）

| # | 指标 | 来源 | 更新频率 |
|---|------|------|----------|
| 1 | 公司名 | Excel（手动） | 不变 |
| 2 | 股票编码 | Excel（手动） | 不变 |
| 3 | 当前股价 | akshare + yfinance 交叉验证 | 每日 |
| 4 | 买入股价 | Excel（手动） | 不变 |
| 5 | 买入 PE | Excel（手动） | 不变 |
| 6 | 当前 PE | akshare + 东方财富 交叉验证 | 每日 |
| 7 | 买入净利润 | Excel（手动） | 不变 |
| 8 | 买入 FCF | Excel（手动） | 不变 |
| 9 | 当前净利润（年报） | 自溯源表 B 区读取 | 年报发布后 |
| 10 | 当前净利润（一致预期） | 东方财富分析师一致预期 | 每日 |
| 11 | 当前 FCF（年报） | 自溯源表 B 区读取 | 年报发布后 |
| 12 | 当前 FCF（一致预期） | 东方财富一致预期反推 | 每日 |
| 13 | 买入预期增速 | Excel（手动） | 不变 |
| 14 | 当前预期增速 | 市场隐含 / 一致预期 | 每日 |
| 15 | 买入预期收益 | Excel（手动） | 不变 |
| 16 | 当前预期收益 | 主观判断（甲方维护）+ 市场隐含（自动算） | 按需 + 每日 |
| 17 | 买入逻辑 | Excel（手动） | 不变 |
| 18 | 护城河 | Excel（手动） | 不变 |
| 19 | 风险因子 | Excel（手动） | 不变 |

> 实际 19 项：买入净利润/FCF 拆为年报+一致预期两行；新增市场隐含指标。

---

## 2. 架构设计

### 整体数据流

```
[甲方 Excel] ──→ Python 脚本 ──→ position_tracker.json ──→ VitePress build ──→ 静态站点
                    ↑                    ↑                      ↑
              akshare + yfinance      买入快照冻结          Vue 持仓卡片组件
              (双源交叉验证<1%)       + 自动抓取当前值       甲方浏览器打开
```

### 交付模式

**本地运行**，不是 GitHub Actions。理由：甲方未必有 GitHub 账号，乙方不需长期维护管线。

- 交付文件夹，含 `一键安装.bat`（装 Python 依赖 + npm 依赖）
- 甲方每天双击 `每日更新.bat`，30 秒刷新数据
- 双击 `site/start.bat` 在浏览器中查看最新看板
- 可选：配 Windows 计划任务实现全自动

### 数据边界（关键）

| 文件 | 维护者 | 频率 | 作用 |
|------|--------|------|------|
| `港股通-泡泡玛特-沪股通-贵州茅台.xlsx` | 甲方手动 | 极低（买入/卖出时） | 买入快照 + 逻辑 |
| `数据溯源/*.md` | 乙方（分析报告流程） | 年报发布后 | S 级财务数据 |
| `position_tracker.json` | Python 脚本自动 | 每日覆盖 | 当前数据集中 |
| `snapshots/*.csv` | Python 脚本自动 | 每日追加 | 历史回溯 |

**溯源表不动**——脚本只读，不写。

---

## 3. JSON 数据结构

### `position_tracker.json`

```json
{
  "meta": {
    "updated_at": "2026-06-12T09:05:00+08:00",
    "version": "1.0",
    "validation": { "total_checks": 4, "passed": 4, "failed": 0, "single_source": 0 }
  },
  "positions": [
    {
      "id": "09992",
      "company": "泡泡玛特",
      "code": "09992.HK",
      "exchange": "港股通",
      "currency": "HKD",

      "buy": {
        "price": 150.107,
        "pe": 14.13,
        "net_profit": { "value": 127.76, "unit": "亿CNY", "year": "FY2025" },
        "fcf": { "value": 96.94, "unit": "亿CNY", "year": "FY2025" },
        "growth_rate": "5年内10%-15%，长期5%",
        "expected_return": "年化15%以上",
        "logic": "1. 最好的商业模式：低库存低资本开支、高毛利、产品差异化大无成本竞争压力 2. 顶级管理团队且核心团队年轻，可以保证管理长期稳定 3.labubu爆火加速品类进入新市场消费者心智，且验证产品的跨文化感召力 4.按labubu销量减一半来计算pe18倍左右，安全边际足够",
        "moat": "独家IP、labubu爆火带来的全球知名度和影响力，公司在消费者心智中代表潮玩品类，管理团队优秀",
        "risk_factor": "潮玩品类整体衰退"
      },

      "current": {
        "price": { "value": null, "source": "akshare+yfinance", "cross_validated": false },
        "pe_ttm": { "value": null, "source": "akshare+eastmoney", "cross_validated": false },
        "net_profit_reported": { "value": 127.76, "unit": "亿CNY", "year": "FY2025", "source": "溯源表-B区" },
        "net_profit_consensus": { "value": null, "unit": "亿CNY", "year": "FY2026E", "source": "东方财富一致预期" },
        "fcf_reported": { "value": 96.94, "unit": "亿CNY", "year": "FY2025", "source": "溯源表-B区" },
        "fcf_consensus": { "value": null, "unit": "亿CNY", "year": "FY2026E", "source": "东方财富一致预期" },
        "growth_consensus": { "value": null, "source": "一致预期反推" },
        "market_implied": {
          "implied_growth": null,
          "implied_return": null,
          "growth_note": "当前PE反推市场隐含永续增速，假设折现率10%",
          "return_note": "隐含增速 → 预期年化收益（含分红）"
        },
        "subjective_return": "年化15%以上"
      }
    }
  ]
}
```

### 设计要点

- **current 每个值带 `source`**：甲方随时知道数据从哪来的
- **`cross_validated` 布尔字段**：true = 双源验证通过（<1%），false = 本次验证失败或首次运行
- **年报 vs 一致预期分存**：看板并排展示，甲方自己判断
- **`market_implied`**：Python 自动计算，不做估值建议——只做"市场定价翻译"
- **主观字段保留**：`subjective_return` 甲方自己维护（可改 position_tracker.json 或未来加一个小 UI）

---

## 4. 交叉验证规则

### 股价验证

```
|akshare_adj_close - yfinance_adj_close| / max(akshare, yfinance) < 0.01  → cross_validated = true
```

- 两个来源都用复权收盘价
- 港股：akshare 为主，yfinance 为校对
- A 股：akshare 为主，yfinance/东方财富为校对

### PE(TTM) 验证

```
|akshare_pe_ttm - eastmoney_pe_ttm| / eastmoney_pe_ttm < 0.01  → cross_validated = true
```

- akshare 直接取 `stock_individual_info_em` 接口
- 如果只有单源可用，标记 `cross_validated = false, source_single = true`，看板上显示 `?`

### 一致预期验证

一致预期难以双源交叉验证（东方财富和同花顺的数据源重叠严重）。策略：
- 单源抓取，标记 `single_source = true`
- 看板展示时加 `[单源]` 标签
- 如果抓取失败（返回 null），不阻塞整体流程

### 验证失败处理

- 任一验证失败 → meta.validation.failed += 1
- 不阻塞 JSON 写出（甲方仍能查看看板）
- 看板顶部警告条："⚠ 今日有 N 项数据验证未通过，请手动核实"
- 失败字段在卡片中标记 `✗` + 红色

---

## 5. 看板页面设计

### 视觉风格

- VitePress 默认主题容器内渲染
- 浅色底（VitePress 原生风格），深色模式自动跟随
- 每只股票一张"持仓卡片"，卡片并排或上下排列

### 单张卡片布局

```
┌─────────────────────────────────────────────────────────────┐
│ 泡泡玛特                              09992.HK  [港股通]    │  标题栏
│ ─────────────────────────────────────────────────────────── │
│                                                             │
│ 当前股价           买入股价          盈亏                     │
│ HK$158.30          HK$150.11         +5.5% ▲               │  价格区（大字号）
│ [akshare+yfinance ✓]  [Excel]        [+HK$8.19]            │
│                                                             │
│ ◆ 估值变化                          ◆ 基本面（年报 / 一致预期）│
│ ┌──────────────────┐  ┌──────────────────────────────────┐ │
│ │指标    买入   当前 │  │项目      年报(FY2025)  FY2026E  │ │
│ │PE     14.13  15.80│  │净利润     127.76亿    ———      │ │
│ │增速   10-15% ——  │  │FCF        96.94亿     ———      │ │
│ └──────────────────┘  └──────────────────────────────────┘ │
│                                                             │
│ ◆ 预期收益（双轨）                    关注度: 🟡 medium       │
│ ┌──────────────────┬─────────────────────────────────────┐ │
│ │ 我的判断（主观）   │ 市场隐含（客观）                      │ │
│ │ 年化 15%+        │ 隐含增速 ~8% → 年化 ~10%             │ │
│ │ 买入时: 年化15%+ │ 解读: 市场给的隐含增速比你的预期低    │ │
│ └──────────────────┴─────────────────────────────────────┘ │
│                                                             │
│ ◆ 投资逻辑 & 风险                          [展开 ▼]           │
│ [+] 买入逻辑: 最好的商业模式，低库存低资本开支...              │
│ [🛡] 护城河: 独家IP、labubu爆火带来的全球知名度...            │
│ [⚠] 风险因子: 潮玩品类整体衰退                               │
│                                                             │
│ 数据更新时间: 2026-06-12 09:05  |  交叉验证: ✓全部通过      │
└─────────────────────────────────────────────────────────────┘
```

### 颜色编码

| 颜色 | 含义 | 触发条件 |
|------|------|----------|
| 🟢 绿 | 当前值优于买入时 | PE 更低 / 隐含回报 > 买入预期 / 盈利超预期 |
| 🟡 黄 | 中性或数据部分缺失 | 主观-市场分歧中等 / 单源数据 |
| 🔴 红 | 当前值劣于买入时 | PE 更高 / 盈利下滑 / 隐含回报 < 5% / 交叉验证失败 |
| ⚪ 灰 | 数据缺失 | 一致预期暂无 |

### 交叉验证标记

- `✓`：双源验证通过（<1%误差）
- `✗`：验证失败（>1%或仅单源）
- `?`：单源数据，无法验证

### 顶层状态栏

```
┌──────────────────────────────────────────────┐
│  📊 数据状态: ✓ 验证通过 (4/4)               │
│  🕐 最后更新: 2026-06-12 09:05               │
│  📈 组合总盈亏: +5.2%   |  关注股票: 2       │
└──────────────────────────────────────────────┘
```

---

## 6. 技术实现

### 文件清单（乙方需创建/修改）

| 文件 | 类型 | 职责 |
|------|------|------|
| `scripts/update_position_tracker.py` | 新建 | 核心引擎：读Excel → 抓取 → 验证 → 计算 → 写JSON + CSV |
| `data/position_tracker.json` | 自动生成 | 当前数据集（VitePress 数据源） |
| `data/snapshots/` | 目录 | 每日 CSV 快照留底 |
| `docs/positions/index.md` | 新建 | VitePress 页面，引用 Vue 组件 |
| `docs/.vitepress/theme/components/PositionCard.vue` | 新建 | Vue 3 持仓卡片组件 |
| `docs/.vitepress/config.js` | 修改 | 添加 positions 页面到导航 |
| `一键安装.bat` | 新建 | Python + npm 依赖安装 |
| `每日更新.bat` | 新建 | 一键运行更新脚本 + VitePress build |
| `site/start.bat` | 新建 | 启动 VitePress dev server |
| `使用说明.md` | 新建 | 甲方操作手册 |

### 关键依赖

**Python**：
- `akshare` — A 股/港股行情 + 东方财富一致预期
- `yfinance` — 港股历史价格（验证用）
- `openpyxl` — 读取甲方 Excel

**Node.js / VitePress**：
- `vitepress` — 站点框架
- `vue` — 组件渲染（VitePress 内置）

### VitePress 集成方式

```js
// docs/.vitepress/config.js 新增
export default {
  themeConfig: {
    nav: [
      { text: '持仓看板', link: '/positions/' }
    ],
    sidebar: { '/positions/': [] }  // 无侧栏，卡片铺满
  }
}
```

```vue
<!-- docs/.vitepress/theme/components/PositionCard.vue -->
<template>
  <div class="position-card" :class="statusClass">
    <!-- 标题栏 -->
    <!-- 价格区 -->
    <!-- 估值对比表 -->
    <!-- 基本面双轨表 -->
    <!-- 预期收益双轨 -->
    <!-- 逻辑/护城河/风险（折叠） -->
    <!-- 页脚（更新时间 + 验证状态） -->
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
// Props: position data from position_tracker.json
// 计算: 盈亏%、关注度、颜色编码
</script>
```

```markdown
<!-- docs/positions/index.md -->
---
title: 持仓追踪看板
---

<PositionCards />
```

---

## 7. Python 脚本核心逻辑

### `update_position_tracker.py` 伪代码

```python
# 1. 读取买入数据
buy_data = read_excel("港股通-泡泡玛特-沪股通-贵州茅台.xlsx")

# 2. 读取现有 position_tracker.json（保留甲方手动修改的字段）
old_data = read_json("position_tracker.json") or {}

# 3. 抓取当前数据 + 交叉验证
for position in buy_data:
    code = position.code
    market = "HK" if code.endswith(".HK") else "A"

    # 股价：akshare + yfinance 双源
    p1 = akshare.get_price(code)
    p2 = yfinance.get_price(code)
    price, validated = cross_validate(p1, p2, 0.01)

    # PE(TTM)：akshare + 东方财富
    pe1 = akshare.get_pe_ttm(code)
    pe2 = eastmoney.get_pe_ttm(code)
    pe, pe_validated = cross_validate(pe1, pe2, 0.01)

    # 一致预期
    consensus = akshare.get_analyst_consensus(code)  # 单源

    # 年报数据：读取溯源表 B 区
    reported = read_traceability_table(f"数据溯源/{position.company}_{code}_数据溯源表.md")

    # 市场隐含计算
    market_implied = compute_implied_growth(pe.value, position.buy.net_profit.value)

    # 写入 current 块
    position.current = { price, pe_ttm, net_profit_reported, ... }

# 4. 写出 JSON
write_json("position_tracker.json", positions)

# 5. 追加 CSV 快照
append_csv_snapshot("snapshots/{date}.csv", positions)

# 6. VitePress build
subprocess.run(["npm", "run", "docs:build"], cwd="site")
```

---

## 8. 交付清单

### 乙方交付物

| # | 文件 | 说明 |
|---|------|------|
| 1 | `持仓追踪看板/` 文件夹（完整） | 甲方解压即用 |
| 2 | `一键安装.bat` | 首次环境安装 |
| 3 | `每日更新.bat` | 每日数据刷新 |
| 4 | `使用说明.md` | 操作手册（含 Windows 计划任务配置步骤） |

### 甲方环境要求

- Windows 10/11
- Python 3.8+（如未安装，bat 脚本会提示下载）
- Node.js 18+（如未安装，bat 脚本会提示下载）
- 网络连接（抓取数据需要）

### 乙方不负责

- 甲方电脑的 Python/Node 安装（bat 脚本会检测并提示）
- 数据源的长期可用性（akshare/yfinance 为开源项目）
- 甲方手动修改 position_tracker.json 导致的格式错误

---

## 9. 验收标准

1. 泡泡玛特和茅台的数据抓取成功，交叉验证通过率 ≥ 80%
2. 看板页面本地 `npm run docs:dev` 启动后，浏览器可见两张持仓卡片
3. 卡片正确展示：股价+盈亏、PE对比、年报/一致预期双表、预期收益双轨、买入逻辑折叠区
4. `每日更新.bat` 一键运行到 VitePress build 完成（< 2 分钟）
5. `一键安装.bat` 在新 Windows 环境可完成环境初始化
