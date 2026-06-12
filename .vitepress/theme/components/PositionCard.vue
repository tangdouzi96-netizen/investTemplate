<script setup>
import { computed } from 'vue'

const props = defineProps({
  position: {
    type: Object,
    required: true
  }
})

// ── Formatters ──
function fmtPrice(value, currency) {
  if (value == null || isNaN(value)) return '—'
  const prefix = currency === 'HKD' ? 'HK$' : '¥'
  return `${prefix}${Number(value).toFixed(2)}`
}

function fmtPE(value) {
  if (value == null || isNaN(value)) return '—'
  return Number(value).toFixed(2)
}

function fmtPct(value) {
  if (value == null || isNaN(value)) return '—'
  return `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(2)}%`
}

function fmtNumber(value, unit) {
  if (value == null || isNaN(value)) return '—'
  const suffix = unit ? ` ${unit}` : ''
  return `${Number(value).toFixed(2)}${suffix}`
}

function fmtImplied(value) {
  if (value == null || isNaN(value)) return '—'
  return `${Number(value).toFixed(2)}%`
}

// ── Computed ──
const pnlPct = computed(() => {
  const cur = props.position.current?.price?.value
  const buy = props.position.buy?.price
  if (cur == null || buy == null || !buy) return null
  return ((cur / buy) - 1) * 100
})

const pnlAbs = computed(() => {
  const cur = props.position.current?.price?.value
  const buy = props.position.buy?.price
  if (cur == null || buy == null) return null
  return cur - buy
})

const peDirection = computed(() => {
  const curPE = props.position.current?.pe_ttm?.value
  const buyPE = props.position.buy?.pe
  if (curPE == null || buyPE == null) return 'neutral'
  if (curPE < buyPE) return 'good'
  if (curPE > buyPE) return 'bad'
  return 'neutral'
})

const npDirection = computed(() => {
  const cur = props.position.current?.net_profit_reported?.value
  const buy = props.position.buy?.net_profit
  if (cur == null || buy == null) return 'neutral'
  if (cur > buy) return 'good'
  if (cur < buy) return 'bad'
  return 'neutral'
})

const fcfDirection = computed(() => {
  const cur = props.position.current?.fcf_reported?.value
  const buy = props.position.buy?.fcf
  if (cur == null || buy == null) return 'neutral'
  if (cur > buy) return 'good'
  if (cur < buy) return 'bad'
  return 'neutral'
})

const divergenceLevel = computed(() => {
  const g = props.position.current?.market_implied?.implied_growth
  if (g == null) return 'unknown'
  if (g < 3) return 'high'
  if (g <= 6) return 'medium'
  return 'low'
})

const divergenceLabel = computed(() => {
  const map = { high: '⚠️ 主观与市场差异大', medium: '⚠ 主观与市场有差异', low: '✅ 主观与市场一致', unknown: '❓ 市场数据缺失' }
  return map[divergenceLevel.value] || '❓ 市场数据缺失'
})

const validationSummary = computed(() => {
  const priceOK = props.position.current?.price?.cross_validated === true
  const peOK = props.position.current?.pe_ttm?.cross_validated === true
  const total = 2
  const passed = (priceOK ? 1 : 0) + (peOK ? 1 : 0)
  return { total, passed, failed: total - passed, priceOK, peOK }
})
</script>

<template>
  <div class="position-card">
    <!-- Header -->
    <div class="card-header">
      <div class="card-title">
        <span class="company-name">{{ position.company }}</span>
        <span class="stock-code">{{ position.code }}</span>
        <span class="exchange-tag">{{ position.exchange }}</span>
      </div>
    </div>

    <!-- Price Row -->
    <div class="card-price-row">
      <div class="price-item">
        <div class="price-label">当前价格</div>
        <div class="price-value current">{{ fmtPrice(position.current?.price?.value, position.currency) }}</div>
        <div class="price-source" :class="position.current?.price?.cross_validated ? 'validated' : ''">
          {{ position.current?.price?.source || '—' }}
          <span v-if="position.current?.price?.cross_validated"> ✓</span>
        </div>
      </div>
      <div class="price-item">
        <div class="price-label">买入成本</div>
        <div class="price-value buy">{{ fmtPrice(position.buy?.price, position.currency) }}</div>
        <div class="price-source">买入均价</div>
      </div>
      <div class="price-item">
        <div class="price-label">持仓盈亏</div>
        <div class="price-value" :class="pnlPct != null && pnlPct >= 0 ? 'up' : 'down'">
          <span v-if="pnlPct != null">{{ fmtPct(pnlPct) }}</span>
          <span v-else>—</span>
        </div>
        <div class="price-source" :class="pnlAbs != null && pnlAbs >= 0 ? 'up-source' : 'down-source'">
          {{ pnlAbs != null ? fmtPrice(pnlAbs, position.currency) : '—' }}
        </div>
      </div>
    </div>

    <!-- Tables Row: PE + Fundamentals with buy comparison -->
    <div class="card-tables-row">
      <!-- PE Comparison -->
      <div class="card-table">
        <h4>📈 PE 估值对比</h4>
        <table>
          <thead>
            <tr><th>指标</th><th>买入</th><th>当前</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>PE</td>
              <td>{{ fmtPE(position.buy?.pe) }}</td>
              <td :class="peDirection">
                {{ fmtPE(position.current?.pe_ttm?.value) }}
                <span v-if="peDirection === 'good'"> ↓</span>
                <span v-if="peDirection === 'bad'"> ↑</span>
              </td>
            </tr>
            <tr>
              <td>预期增速</td>
              <td colspan="2" style="color:var(--vp-c-text-2);">{{ position.buy?.growth_rate || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Fundamentals with buy comparison -->
      <div class="card-table">
        <h4>📊 盈利与现金流</h4>
        <table>
          <thead>
            <tr><th>指标</th><th>买入</th><th>当前(年报)</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>净利润</td>
              <td>{{ fmtNumber(position.buy?.net_profit, '亿') }}</td>
              <td :class="npDirection">
                {{ fmtNumber(position.current?.net_profit_reported?.value, '亿') }}
                <span v-if="npDirection === 'good'"> ↑</span>
                <span v-if="npDirection === 'bad'"> ↓</span>
              </td>
            </tr>
            <tr>
              <td>自由现金流</td>
              <td>{{ fmtNumber(position.buy?.fcf, '亿') }}</td>
              <td :class="fcfDirection">
                {{ fmtNumber(position.current?.fcf_reported?.value, '亿') }}
                <span v-if="fcfDirection === 'good'"> ↑</span>
                <span v-if="fcfDirection === 'bad'"> ↓</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Returns Row -->
    <div class="card-returns-row">
      <h4>
        📈 预期收益双轨
        <span class="divergence-badge" :class="divergenceLevel">{{ divergenceLabel }}</span>
      </h4>
      <div class="returns-dual">
        <div class="return-box subjective">
          <div class="return-box-title">🧠 我的判断（主观）</div>
          <div class="return-box-value">{{ position.current?.subjective_return || position.buy?.expected_return || '—' }}</div>
          <div class="return-box-note">基于深度研究与估值模型</div>
        </div>
        <div class="return-box market">
          <div class="return-box-title">📊 市场隐含（客观）</div>
          <div class="return-box-value">
            <template v-if="position.current?.market_implied?.implied_return != null">
              预期收益 {{ fmtImplied(position.current.market_implied.implied_return) }}
            </template>
            <template v-else>—</template>
          </div>
          <div class="return-box-note">
            隐含增速：
            <template v-if="position.current?.market_implied?.implied_growth != null">
              {{ fmtImplied(position.current.market_implied.implied_growth) }}
            </template>
            <template v-else>数据不足</template>
            &nbsp;（PE反推，折现率10%）
          </div>
        </div>
      </div>
    </div>

    <!-- Collapsible Details -->
    <details class="card-details">
      <summary>📝 投资逻辑与护城河</summary>
      <div class="detail-item logic" v-if="position.buy?.logic">
        <strong>买入逻辑：</strong>
        <p>{{ position.buy.logic }}</p>
      </div>
      <div class="detail-item moat" v-if="position.buy?.moat">
        <strong>护城河：</strong>
        <p>{{ position.buy.moat }}</p>
      </div>
      <div class="detail-item risk" v-if="position.buy?.risk_factor">
        <strong>风险因子：</strong>
        <p>{{ position.buy.risk_factor }}</p>
      </div>
    </details>

    <!-- Footer -->
    <div class="card-footer">
      数据校验：价格{{ validationSummary.priceOK ? '✓' : '✗' }}
      &nbsp;|&nbsp; PE{{ validationSummary.peOK ? '✓' : '✗' }}
      &nbsp;|&nbsp; {{ validationSummary.passed }}/{{ validationSummary.total }} 通过
    </div>
  </div>
</template>
