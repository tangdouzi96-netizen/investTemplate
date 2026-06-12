<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { withBase } from 'vitepress'

// #region agent log
function debugLayoutMetrics(runId = 'pre-fix') {
  const vpDoc = document.querySelector('.VPDoc')
  const container = document.querySelector('.VPDoc .container')
  const content = document.querySelector('.VPDoc .container .content')
  const contentContainer = document.querySelector('.VPDoc .content-container')
  const rdRoot = document.querySelector('.rd-root')
  const tblCard = document.querySelector('.rd-tbl-card')
  const noteCell = document.querySelector('.td-note')
  const cs = (el) => (el ? getComputedStyle(el) : null)
  const payload = {
    sessionId: '4561a6',
    runId,
    timestamp: Date.now(),
    location: 'RiskDashboard.vue:debugLayoutMetrics',
    message: 'risk dashboard layout metrics',
    data: {
      pathname: window.location.pathname,
      isStandalonePage: !!document.querySelector('.sidebar:not(.rd-sidebar)') && !document.querySelector('.rd-root'),
      isVueDashboard: !!document.querySelector('.rd-root'),
      bodyClasses: document.body.className,
      vpDocHasAside: vpDoc?.classList.contains('has-aside') ?? null,
      viewportWidth: window.innerWidth,
      container: container ? { clientWidth: container.clientWidth, maxWidth: cs(container).maxWidth } : null,
      contentContainer: contentContainer ? { clientWidth: contentContainer.clientWidth, maxWidth: cs(contentContainer).maxWidth } : null,
      content: content ? { clientWidth: content.clientWidth, maxWidth: cs(content).maxWidth } : null,
      rdRoot: rdRoot ? { clientWidth: rdRoot.clientWidth } : null,
      tblCard: tblCard ? { clientWidth: tblCard.clientWidth, overflow: cs(tblCard).overflow } : null,
      noteCell: noteCell ? { clientWidth: noteCell.clientWidth, scrollWidth: noteCell.scrollWidth, truncated: noteCell.scrollWidth > noteCell.clientWidth, maxWidth: cs(noteCell).maxWidth } : null,
      dotSample: (() => {
        const dot = document.querySelector('.rd-tbl .dot')
        if (!dot) return null
        const dotCs = cs(dot)
        const rootCs = getComputedStyle(document.documentElement)
        return {
          className: dot.className,
          width: dotCs.width,
          height: dotCs.height,
          background: dotCs.backgroundColor,
          display: dotCs.display,
          cssVarG: rootCs.getPropertyValue('--g').trim(),
          cssVarOnRdRoot: (() => {
            const root = document.querySelector('.rd-root')
            return root ? getComputedStyle(root).getPropertyValue('--g').trim() : null
          })(),
        }
      })(),
    },
    hypothesisId: 'A-E',
  }
  fetch('http://127.0.0.1:7510/ingest/6be7b03f-4dfd-45af-8445-b6bf69318ae9', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '4561a6' }, body: JSON.stringify(payload) }).catch(() => {})
}
// #endregion

const loading = ref(true)
const riskData = ref(null)
const activeCompany = ref(null)
const currentView = ref('snapshot')
const years = ['2021', '2022', '2023', '2024', '2025']
const icons = { '泸州老窖': '🍶', '泡泡玛特': '🧸', '陕西煤业': '⛏️' }

const companies = computed(() => riskData.value?.companies || {})
const active = computed(() => activeCompany.value ? riskData.value?.companies[activeCompany.value] : null)

const confTitle = { S:'年报PDF原文→可全额建仓', A:'官网/业绩公告→可正常分析', B:'第三方平台→需交叉验证', C:'研报/业内估算→仅供参考', D:'AI估算→禁止用于投资决策' }

function dotClass(s) {
  if (s === 'green') return 'dot-g'; if (s === 'yellow') return 'dot-y'; if (s === 'red') return 'dot-r'; return 'dot-x'
}
function trendIcon(t) {
  if (t === '↑') return '↑'; if (t === '↓') return '↓'; if (t === '→') return '→'; return '—'
}
function trendCls(t) {
  if (t === '↑') return 't-up'; if (t === '↓') return 't-dn'; return 't-flat'
}
function statusInfo(c) {
  if (c.status === 'normal') return { clr: '#22c55e', txt: '🟢 正常' }
  if (c.status === 'warning') return { clr: '#eab308', txt: '🟡 关注' }
  return { clr: '#ef4444', txt: '🔴 预警' }
}

async function loadData() {
  try {
    const r = await fetch(withBase('/risk-data.json'), { cache: 'no-store' })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    riskData.value = await r.json()
    loading.value = false
    const first = Object.keys(riskData.value.companies)[0]
    if (first) selectCompany(first)
    await nextTick()
    // #region agent log
    requestAnimationFrame(() => debugLayoutMetrics('post-fix'))
    // #endregion
  } catch (e) {
    loading.value = false
  }
}

function selectCompany(name) {
  activeCompany.value = name; currentView.value = 'snapshot'
}

onMounted(() => {
  document.body.classList.add('dashboard-wide', 'risk-dashboard-active')
  loadData()
})
onBeforeUnmount(() => {
  document.body.classList.remove('dashboard-wide', 'risk-dashboard-active')
})
</script>

<template>
  <div v-if="loading" class="rd-loading">加载中...</div>
  <div v-else-if="!riskData" class="rd-loading">数据加载失败</div>
  <div v-else class="rd-root">
    <!-- Sidebar -->
    <aside class="rd-sidebar">
      <div class="rd-sb-hd">⚠️ 风险跟踪</div>
      <div class="rd-sb-list">
        <div v-for="(c, name) in companies" :key="name"
          class="rd-sb-item" :class="{ active: activeCompany === name }"
          @click="selectCompany(name)">
          <span class="rd-sb-icon">{{ icons[name] || '📊' }}</span>
          <div class="rd-sb-info">
            <div class="rd-sb-name">{{ name }}</div>
            <div class="rd-sb-code">{{ c.code }}</div>
            <div class="rd-sb-st" :style="{ color: statusInfo(c).clr }">
              {{ statusInfo(c).txt }}
              <template v-if="c.indicators">
                · {{ c.indicators.filter(i => i.status === 'red').length }}🔴
                {{ c.indicators.filter(i => i.status === 'yellow').length }}🟡
              </template>
            </div>
          </div>
        </div>
      </div>
      <div class="rd-sb-ft">年报(S级) + 公开市场数据(B级)</div>
    </aside>

    <!-- Main -->
    <main class="rd-main">
      <div v-if="!active" class="rd-empty">
        <div class="rd-empty-icon">👈</div>
        <div>从左侧选择一家公司查看风险跟踪指标</div>
      </div>
      <template v-else>
        <header class="rd-hd">
          <div class="rd-hd-left">
            <h2>{{ activeCompany }}</h2>
            <span class="rd-tag">{{ active.code }}</span>
            <span class="rd-tag">{{ active.industry }}</span>
            <span class="rd-tag">{{ active.assetType }}</span>
            <span class="rd-tag">FCF/NP {{ active.fcfThreshold }}</span>
          </div>
          <div class="rd-hd-right">
            <span class="rd-update">最后更新：{{ riskData.lastUpdated }}</span>
          </div>
        </header>

        <!-- Status bar -->
        <div class="rd-bar">
          <span class="rd-bar-item">
            <span class="rd-bar-lbl">状态</span>
            <span class="rd-bar-val" :style="{ color: statusInfo(active).clr }">{{ statusInfo(active).txt }}</span>
          </span>
          <span class="rd-bar-item">
            <span class="rd-bar-lbl">🔴 预警</span>
            <span class="rd-bar-val" style="color:#ef4444">{{ active.indicators.filter(i => i.status === 'red').length }}</span>
          </span>
          <span class="rd-bar-item">
            <span class="rd-bar-lbl">🟡 关注</span>
            <span class="rd-bar-val" style="color:#eab308">{{ active.indicators.filter(i => i.status === 'yellow').length }}</span>
          </span>
          <span class="rd-bar-item">
            <span class="rd-bar-lbl">⬜ 待更新</span>
            <span class="rd-bar-val" style="color:var(--vp-c-text-3)">{{ active.indicators.filter(i => i.status === 'unknown').length }}</span>
          </span>
        </div>

        <!-- View toggle -->
        <div class="rd-tog-bar">
          <div class="rd-tog-group">
            <button class="rd-tog-btn" :class="{ active: currentView === 'snapshot' }" @click="currentView = 'snapshot'">📸 快照</button>
            <button class="rd-tog-btn" :class="{ active: currentView === 'history' }" @click="currentView = 'history'">📅 历史追溯</button>
          </div>
          <span class="rd-tog-note">{{ currentView === 'history' ? '5年并排对比' : '最新数据快照' }}</span>
        </div>

        <!-- Snapshot Table -->
        <div v-if="currentView === 'snapshot'" class="rd-tbl-card">
          <table class="rd-tbl">
            <thead>
              <tr>
                <th class="w-dim">维度</th>
                <th class="w-name">指标</th>
                <th class="w-val">当前值</th>
                <th class="w-thr">阈值</th>
                <th class="w-trend">趋势</th>
                <th class="w-conf">置信度</th>
                <th>备注</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(ind, idx) in active.indicators" :key="idx"
                :class="{ 'dim-sep': ind.dim.startsWith('🔍') }">
                <td class="td-dim">{{ ind.dim }}</td>
                <td>{{ ind.name }}</td>
                <td class="td-mono"><span class="dot" :class="dotClass(ind.status)"></span>{{ ind.value }}</td>
                <td class="td-muted">{{ ind.threshold }}</td>
                <td><span :class="trendCls(ind.trend)">{{ trendIcon(ind.trend) }}</span></td>
                <td style="text-align:center"><span class="conf-b" :class="'c-' + (ind.confidence || 'D')" :title="confTitle[ind.confidence]">{{ ind.confidence || 'D' }}</span></td>
                <td class="td-note" :title="ind.note">{{ ind.note || '' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- History Table -->
        <div v-else class="rd-tbl-card rd-matrix">
          <table class="rd-tbl">
            <thead>
              <tr>
                <th class="w-dim">维度</th>
                <th class="w-name">指标</th>
                <th v-for="yr in years" :key="yr" class="w-year">{{ yr }}</th>
                <th class="w-thr">阈值</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(ind, idx) in active.indicators" :key="idx"
                :class="{ 'dim-sep': ind.dim.startsWith('🔍') }">
                <td class="td-dim">{{ ind.dim }}</td>
                <td>{{ ind.name }}</td>
                <td v-for="yr in years" :key="yr" class="td-mono" style="text-align:center">
                  <template v-if="ind.history && ind.history[yr]">
                    <span class="dot" :class="dotClass(ind.history[yr].status)"></span>{{ ind.history[yr].value }}
                  </template>
                  <span v-else style="color:var(--vp-c-text-3);font-style:italic">—</span>
                </td>
                <td class="td-muted">{{ ind.threshold }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
/* ── semantic colors (on .rd-root so scoped vars cascade to dots/badges) ── */
.rd-root { --rd-g: #22c55e; --rd-gb: rgba(34,197,94,.12); --rd-y: #eab308; --rd-yb: rgba(234,179,8,.12); --rd-r: #ef4444; --rd-rb: rgba(239,68,68,.12); --rd-o: #f97316; --rd-ob: rgba(249,115,22,.15); display: flex; }
.rd-loading { padding: 60px; text-align: center; color: var(--vp-c-text-3); }

/* ── sidebar ── */
.rd-sidebar { width: 195px; min-width: 195px; background: var(--vp-c-bg-soft); border-right: 1px solid var(--vp-c-divider); display: flex; flex-direction: column; position: sticky; top: 64px; align-self: flex-start; max-height: calc(100vh - 64px); overflow-y: auto; }
.rd-sb-hd { padding: 16px 16px 12px; border-bottom: 1px solid var(--vp-c-divider); font-size: .9rem; font-weight: 700; color: var(--vp-c-text-1); }
.rd-sb-list { flex: 1; overflow-y: auto; }
.rd-sb-item { display: flex; align-items: center; gap: 8px; padding: 10px 16px; cursor: pointer; border-left: 3px solid transparent; transition: all .15s; }
.rd-sb-item:hover { background: var(--vp-c-bg-alt); }
.rd-sb-item.active { background: var(--vp-c-brand-soft); border-left-color: var(--vp-c-brand-1); }
.rd-sb-icon { font-size: 1.1rem; width: 22px; text-align: center; flex-shrink: 0; }
.rd-sb-info { flex: 1; min-width: 0; }
.rd-sb-name { font-size: .85rem; font-weight: 600; color: var(--vp-c-text-1); }
.rd-sb-code { font-size: .68rem; color: var(--vp-c-text-3); }
.rd-sb-st { font-size: .68rem; margin-top: 1px; }
.rd-sb-ft { padding: 10px 16px; border-top: 1px solid var(--vp-c-divider); font-size: .65rem; color: var(--vp-c-text-3); }

/* ── main ── */
.rd-main { flex: 1; min-width: 0; padding: 20px 28px 40px; }
.rd-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 8px; }
.rd-hd-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.rd-hd-left h2 { font-size: 1.15rem; font-weight: 700; color: var(--vp-c-text-1); margin: 0; }
.rd-tag { font-size: .68rem; padding: 1px 7px; border-radius: 99px; background: var(--vp-c-brand-soft); color: var(--vp-c-brand-1); }
.rd-update { font-size: .73rem; color: var(--vp-c-text-3); }

/* ── status bar ── */
.rd-bar { display: flex; gap: 16px; margin-bottom: 12px; padding: 10px 16px; background: var(--vp-c-bg-soft); border: 1px solid var(--vp-c-divider); border-radius: 8px; flex-wrap: wrap; }
.rd-bar-item { display: flex; align-items: center; gap: 6px; font-size: .8rem; }
.rd-bar-lbl { color: var(--vp-c-text-3); }
.rd-bar-val { font-weight: 600; }

/* ── view toggle ── */
.rd-tog-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 6px; }
.rd-tog-group { display: flex; background: var(--vp-c-bg-soft); border: 1px solid var(--vp-c-divider); border-radius: 5px; overflow: hidden; }
.rd-tog-btn { padding: 4px 14px; font-size: .75rem; cursor: pointer; background: transparent; color: var(--vp-c-text-3); border: none; font-weight: 500; }
.rd-tog-btn:not(:last-child) { border-right: 1px solid var(--vp-c-divider); }
.rd-tog-btn:hover { color: var(--vp-c-text-1); background: var(--vp-c-bg-alt); }
.rd-tog-btn.active { background: var(--vp-c-brand-1); color: var(--vp-c-white); }
.rd-tog-note { font-size: .68rem; color: var(--vp-c-text-3); }

/* ── table ── */
.rd-tbl-card { background: var(--vp-c-bg-soft); border: 1px solid var(--vp-c-divider); border-radius: 8px; overflow-x: auto; }
.rd-tbl { width: 100%; border-collapse: collapse; table-layout: auto; min-width: 900px; }
.rd-tbl th { background: var(--vp-c-bg-alt); color: var(--vp-c-text-2); font-size: .72rem; font-weight: 500; text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--vp-c-divider); }
.rd-tbl td { padding: 7px 10px; border-bottom: 1px solid var(--vp-c-divider); color: var(--vp-c-text-1); font-size: .82rem; }
.rd-tbl tr:last-child td { border-bottom: none; }
.rd-tbl tbody tr:hover td { background: var(--vp-c-bg-alt); }
.rd-tbl tr.dim-sep td { border-top: 2px solid var(--vp-c-brand-1); }
.rd-matrix { overflow-x: auto; }
.rd-matrix th { text-align: center; white-space: nowrap; }
.rd-matrix th:first-child, .rd-matrix th:nth-child(2), .rd-matrix th:last-child { text-align: left; }
.rd-matrix td { text-align: center; }
.rd-matrix td:first-child, .rd-matrix td:nth-child(2), .rd-matrix td:last-child { text-align: left; }

/* ── column widths (min-width hints, table-layout:auto lets 备注 expand) ── */
.w-dim { min-width: 88px; } .w-name { min-width: 110px; } .w-val { min-width: 130px; } .w-thr { min-width: 80px; } .w-trend { min-width: 38px; } .w-conf { min-width: 48px; } .w-year { min-width: 100px; }

/* ── cell styles ── */
.td-dim { color: var(--vp-c-brand-1); font-weight: 500; font-size: .72rem; white-space: nowrap; }
.td-mono { font-family: 'JetBrains Mono', 'Consolas', monospace; font-weight: 600; white-space: nowrap; font-size: .8rem; }
.td-muted { font-family: 'JetBrains Mono', 'Consolas', monospace; color: var(--vp-c-text-3); font-size: .75rem; white-space: nowrap; }
.td-note { color: var(--vp-c-text-3); font-size: .7rem; line-height: 1.55; white-space: normal; word-break: break-word; min-width: 200px; }

/* ── dots ── */
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; vertical-align: middle; flex-shrink: 0; }
.dot-g { background: var(--rd-g); }
.dot-y { background: var(--rd-y); }
.dot-r { background: var(--rd-r); }
.dot-x { background: var(--vp-c-text-3); }

/* ── trend ── */
.t-up { color: var(--rd-g); } .t-dn { color: var(--rd-r); } .t-flat { color: var(--vp-c-text-3); }

/* ── conf badge ── */
.conf-b { display: inline-block; font-size: .65rem; font-weight: 700; padding: 1px 6px; border-radius: 3px; min-width: 18px; text-align: center; }
.c-S, .c-A { background: var(--rd-gb); color: var(--rd-g); }
.c-B { background: var(--rd-yb); color: var(--rd-y); }
.c-C { background: var(--rd-ob); color: var(--rd-o); }
.c-D { background: var(--rd-rb); color: var(--rd-r); }

/* ── empty state ── */
.rd-empty { padding: 80px 20px; text-align: center; color: var(--vp-c-text-3); font-size: .85rem; }
.rd-empty-icon { font-size: 2.5rem; margin-bottom: 10px; }
</style>