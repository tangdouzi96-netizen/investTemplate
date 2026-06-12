<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { withBase } from 'vitepress'
import PositionCard from './PositionCard.vue'

const loading = ref(true)
const error = ref('')
const data = ref(null)
const selectedId = ref(null)

const positions = computed(() => data.value?.positions || [])

const selectedPosition = computed(() => {
  if (!positions.value.length) return null
  if (selectedId.value) {
    return positions.value.find(p => p.id === selectedId.value) || positions.value[0]
  }
  return positions.value[0]
})

function selectCompany(id) {
  selectedId.value = id
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(withBase('/data/position_tracker.json'), { cache: 'no-store' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    data.value = await res.json()
    if (!selectedId.value && data.value.positions.length > 0) {
      selectedId.value = data.value.positions[0].id
    }
  } catch (e) {
    error.value = `加载失败：${e instanceof Error ? e.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

onMounted(() => {
  document.body.classList.add('dashboard-wide')
})
onBeforeUnmount(() => {
  document.body.classList.remove('dashboard-wide')
})
</script>

<template>
  <div class="ps-dashboard">
    <!-- Loading -->
    <div v-if="loading" style="text-align:center;padding:40px;color:var(--vp-c-text-3);">
      ⏳ 加载中...
    </div>

    <!-- Error -->
    <div v-else-if="error" style="text-align:center;padding:40px;color:#ef4444;">
      ❌ {{ error }}
      <br/>
      <button @click="loadData" style="margin-top:12px;padding:6px 20px;border:1px solid var(--vp-c-divider);border-radius:8px;cursor:pointer;background:var(--vp-c-bg-soft);color:var(--vp-c-text-1);font-size:0.9rem;">
        🔄 重试
      </button>
    </div>

    <!-- Dashboard -->
    <template v-else>
      <!-- Status bar -->
      <div class="ps-status-bar">
        <span>🕐 {{ data.meta.updated_at }}</span>
        <span>
          📊 {{ data.meta.validation.passed }}/{{ data.meta.validation.total_checks }} 通过
          <span v-if="data.meta.validation.failed > 0" style="color:#ef4444;">⚠ {{ data.meta.validation.failed }} 项失败</span>
          <span v-else style="color:#22c55e;"> ✓</span>
        </span>
        <span style="margin-left:auto;">📈 共 {{ positions.length }} 只标的</span>
        <button @click="loadData" class="ps-refresh-btn">🔄 刷新</button>
      </div>

      <!-- Sidebar + Content Layout -->
      <div class="ps-layout">
        <!-- Left Sidebar -->
        <div class="ps-sidebar">
          <div class="ps-sidebar-title">持仓列表</div>
          <div
            v-for="pos in positions"
            :key="pos.id"
            class="ps-sidebar-item"
            :class="{ active: selectedPosition && selectedPosition.id === pos.id }"
            @click="selectCompany(pos.id)"
          >
            <div class="ps-sidebar-icon">{{ pos.currency === 'HKD' ? '🇭🇰' : '🇨🇳' }}</div>
            <div class="ps-sidebar-info">
              <div class="ps-sidebar-name">{{ pos.company }}</div>
              <div class="ps-sidebar-code">{{ pos.code }}</div>
            </div>
            <div class="ps-sidebar-arrow">
              <span v-if="pos.current?.price?.value && pos.buy?.price"
                    :style="{ color: pos.current.price.value >= pos.buy.price ? '#22c55e' : '#ef4444' }">
                {{ pos.current.price.value >= pos.buy.price ? '▲' : '▼' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Main Content -->
        <div class="ps-main">
          <PositionCard
            v-if="selectedPosition"
            :key="selectedPosition.id"
            :position="selectedPosition"
          />
          <div v-else style="text-align:center;padding:60px;color:var(--vp-c-text-3);">
            👈 请从左侧选择一只股票
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style>
.ps-dashboard {
  margin-top: 8px;
}

.ps-status-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 18px;
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  font-size: 0.82rem;
  color: var(--vp-c-text-2);
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.ps-refresh-btn {
  padding: 4px 14px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  cursor: pointer;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 0.8rem;
}
.ps-refresh-btn:hover {
  border-color: var(--vp-c-brand);
  color: var(--vp-c-brand);
}

.ps-layout {
  display: flex;
  gap: 20px;
  min-height: 60vh;
}

.ps-sidebar {
  width: 220px;
  min-width: 220px;
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  overflow: hidden;
}

.ps-sidebar-title {
  padding: 14px 16px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--vp-c-text-1);
  border-bottom: 1px solid var(--vp-c-divider);
}

.ps-sidebar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: all 0.15s;
}
.ps-sidebar-item:hover { background: var(--vp-c-bg); }
.ps-sidebar-item.active {
  background: var(--vp-c-brand-soft);
  border-left-color: var(--vp-c-brand);
}

.ps-sidebar-icon {
  font-size: 1rem;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.ps-sidebar-info { flex: 1; min-width: 0; }

.ps-sidebar-name {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--vp-c-text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ps-sidebar-code {
  font-size: 0.7rem;
  color: var(--vp-c-text-3);
  font-family: 'JetBrains Mono', 'Consolas', monospace;
}

.ps-sidebar-arrow { font-size: 0.8rem; flex-shrink: 0; }

.ps-main {
  flex: 1;
  min-width: 0;
}

@media (max-width: 768px) {
  .ps-layout { flex-direction: column; }
  .ps-sidebar { width: 100%; min-width: 0; display: flex; flex-wrap: wrap; padding: 8px; }
  .ps-sidebar-title { display: none; }
  .ps-sidebar-item { border-left: none; border-bottom: 2px solid transparent; padding: 8px 10px; border-radius: 6px; }
  .ps-sidebar-item.active { border-left: none; border-bottom-color: var(--vp-c-brand); }
}
</style>
