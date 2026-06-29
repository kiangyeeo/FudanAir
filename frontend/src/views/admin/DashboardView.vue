<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Calendar, Tickets, TrendCharts, User } from '@element-plus/icons-vue'
import CountUp from '@/components/common/CountUp.vue'
import { adminApi } from '@/api/admin'
import { useAirportStore } from '@/stores/airport'
import type { AdminDashboard } from '@/types/admin'

const dashboard = ref<AdminDashboard | null>(null)
const loading = ref(false)
const airportStore = useAirportStore()

const statCards = [
  { key: 'total_orders', title: '总订单数', icon: Tickets, color: '#2563eb', bg: '#eaf2ff' },
  { key: 'today_orders', title: '今日新增订单', icon: Calendar, color: '#0f9f6e', bg: '#e9f8f1' },
  { key: 'total_users', title: '总用户数', icon: User, color: '#7c3aed', bg: '#f1ecff' },
  { key: 'active_users_30d', title: '活跃用户数', icon: TrendCharts, color: '#c27803', bg: '#fff6dd' },
] as const

function statValue(key: (typeof statCards)[number]['key']) {
  return dashboard.value?.[key] ?? 0
}

const topRoutes = computed(() => dashboard.value?.top_routes ?? [])

const maxRouteCount = computed(() => {
  if (!topRoutes.value.length) return 1
  return Math.max(...topRoutes.value.map((item) => item.order_count), 1)
})

function heatWidth(count: number) {
  return `${Math.max(12, Math.round((count / maxRouteCount.value) * 100))}%`
}

function airportName(code: string) {
  return airportStore.display(code)
}

async function loadDashboard() {
  loading.value = true
  try {
    dashboard.value = await adminApi.getDashboard()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void airportStore.ensureLoaded()
  void loadDashboard()
})
</script>

<template>
  <div v-loading="loading" class="dashboard">
    <section class="summary-grid">
      <div
        v-for="(item, index) in statCards"
        :key="item.key"
        class="stat-card"
        v-motion
        :initial="{ opacity: 0, y: 16 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 360, delay: index * 70 } }"
      >
        <span class="stat-icon" :style="{ color: item.color, background: item.bg }">
          <el-icon><component :is="item.icon" /></el-icon>
        </span>
        <div class="stat-body">
          <span class="stat-title">{{ item.title }}</span>
          <CountUp class="stat-value" :value="statValue(item.key)" />
        </div>
      </div>
    </section>

    <section class="content-grid">
      <div class="revenue-card">
        <div class="revenue-topline">
          <span class="revenue-label">今日成交额</span>
          <span class="revenue-chip">已支付</span>
        </div>
        <div class="revenue-value">
          <span class="cny">¥</span><CountUp :value="dashboard?.today_revenue ?? 0" :decimals="2" />
        </div>
        <span class="revenue-foot">实时统计当日已支付订单总额</span>
      </div>

      <el-card shadow="never" class="route-card">
        <template #header>
          <span>今日热门航线 Top 5</span>
        </template>

        <el-table :data="topRoutes" empty-text="暂无今日成交航线" border class="route-table">
          <el-table-column label="排名" type="index" width="80">
            <template #default="{ $index }">
              <span class="rank-badge">{{ $index + 1 }}</span>
            </template>
          </el-table-column>

          <el-table-column label="出发机场" prop="dep_airport_code" min-width="120">
            <template #default="{ row }">
              <div class="airport-cell">
                <span class="airport-code">{{ row.dep_airport_code }}</span>
                <span class="airport-name">{{ airportName(row.dep_airport_code) }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="到达机场" prop="arr_airport_code" min-width="120">
            <template #default="{ row }">
              <div class="airport-cell">
                <span class="airport-code">{{ row.arr_airport_code }}</span>
                <span class="airport-name">{{ airportName(row.arr_airport_code) }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="订单数" prop="order_count" min-width="140">
            <template #default="{ row }">
              <div class="order-cell">
                <span class="order-count mono-num">{{ row.order_count }}</span>
                <div class="heat-track">
                  <div class="heat-bar" :style="{ width: heatWidth(row.order_count) }" />
                </div>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>
  </div>
</template>

<style scoped lang="scss">
.dashboard {
  display: grid;
  gap: 18px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 110px;
  padding: 20px;
  background: var(--fa-surface);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
  transition: transform var(--fa-dur-base) var(--fa-ease), box-shadow var(--fa-dur-base) var(--fa-ease);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.07);
}

.stat-icon {
  display: grid;
  place-items: center;
  flex: 0 0 46px;
  width: 46px;
  height: 46px;
  border-radius: 12px;
  font-size: 22px;
}

.stat-body {
  display: grid;
  gap: 6px;
}

.stat-title {
  color: var(--fa-text-secondary);
  font-size: 13px;
}

.stat-value {
  color: var(--fa-text);
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.75fr) minmax(520px, 1.25fr);
  gap: 16px;
  align-items: stretch;
}

.revenue-card {
  display: grid;
  align-content: space-between;
  gap: 18px;
  min-height: 230px;
  padding: 24px;
  color: var(--fa-text);
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
  border: 1px solid var(--fa-border);
  border-top: 4px solid var(--fa-brand);
  border-radius: var(--fa-radius);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
}

.revenue-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.revenue-label {
  color: var(--fa-text-secondary);
  font-size: 14px;
  font-weight: 700;
}

.revenue-chip {
  padding: 3px 10px;
  color: #0f9f6e;
  background: #e9f8f1;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.revenue-value {
  display: flex;
  align-items: baseline;
  color: var(--fa-brand-dark);
  font-size: 40px;
  font-weight: 800;
  letter-spacing: 0;
}

.revenue-value .cny {
  margin-right: 2px;
  font-size: 22px;
}

.revenue-foot {
  color: var(--fa-text-tertiary);
  font-size: 12px;
}

.route-card {
  border-radius: var(--fa-radius);
  border: 1px solid var(--fa-border);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
}

.route-card :deep(.el-card__header) {
  color: var(--fa-text);
  font-size: 16px;
  font-weight: 700;
  background: #fff;
  border-bottom: 1px solid var(--fa-border);
}

.route-card :deep(.el-card__body) {
  padding: 0;
}

.route-table :deep(.el-table__header th) {
  color: var(--fa-text-secondary);
  font-weight: 700;
  background: #f8fafc;
}

.route-table :deep(.el-table__row) {
  height: 64px;
}

.route-table :deep(.el-table__row:hover > td) {
  background: #f8fbff;
}

.rank-badge {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  color: var(--fa-brand-dark);
  font-size: 13px;
  font-weight: 800;
  background: #eaf2ff;
  border-radius: 50%;
}

.airport-cell {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.airport-code {
  color: var(--fa-text);
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0;
}

.airport-name {
  overflow: hidden;
  color: var(--fa-text-tertiary);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.order-cell {
  display: grid;
  gap: 6px;
}

.order-count {
  color: var(--fa-text);
  font-size: 16px;
  font-weight: 800;
}

.heat-track {
  height: 8px;
  overflow: hidden;
  background: #edf2f7;
  border-radius: 999px;
}

.heat-bar {
  height: 100%;
  background: linear-gradient(90deg, #2563eb, #0f9f6e);
  border-radius: inherit;
}

@media (max-width: 1080px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>