<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { adminApi } from '@/api/admin'
import type { AdminDashboard } from '@/types/admin'

const dashboard = ref<AdminDashboard | null>(null)
const loading = ref(false)

const statCards = [
  { key: 'total_orders', title: '总订单数' },
  { key: 'today_orders', title: '今日新增订单' },
  { key: 'total_users', title: '总用户数' },
  { key: 'active_users_30d', title: '活跃用户数' },
] as const

function statValue(key: (typeof statCards)[number]['key']) {
  return dashboard.value?.[key] ?? 0
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
  }).format(value)
}

const topRoutes = computed(() => dashboard.value?.top_routes ?? [])

const maxRouteCount = computed(() => {
  if (!topRoutes.value.length) return 1
  return Math.max(...topRoutes.value.map((item) => item.order_count), 1)
})

function heatWidth(count: number) {
  return `${Math.max(12, Math.round((count / maxRouteCount.value) * 100))}%`
}

async function loadDashboard() {
  loading.value = true
  try {
    dashboard.value = await adminApi.getDashboard()
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <div v-loading="loading" class="dashboard">
    <section class="summary-grid">
      <el-card v-for="item in statCards" :key="item.key" shadow="never" class="stat-card">
        <el-statistic :title="item.title" :value="statValue(item.key)" />
      </el-card>
    </section>

    <section class="content-grid">
      <el-card shadow="never" class="revenue-card">
        <template #header>
          <span>今日成交额</span>
        </template>
        <div class="revenue-value mono-num">
          {{ formatCurrency(dashboard?.today_revenue ?? 0) }}
        </div>
      </el-card>

      <el-card shadow="never" class="route-card">
        <template #header>
          <span>今日热门航线 Top 5</span>
        </template>

        <el-table
          :data="topRoutes"
          empty-text="暂无今日成交航线"
          border
          class="route-table"
        >
          <el-table-column label="排名" type="index" width="80">
            <template #default="{ $index }">
              <span class="rank-badge">{{ $index + 1 }}</span>
            </template>
          </el-table-column>

          <el-table-column label="出发机场" prop="dep_airport_code" min-width="120">
            <template #default="{ row }">
              <span class="airport-code">{{ row.dep_airport_code }}</span>
            </template>
          </el-table-column>

          <el-table-column label="到达机场" prop="arr_airport_code" min-width="120">
            <template #default="{ row }">
              <span class="airport-code">{{ row.arr_airport_code }}</span>
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
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stat-card,
.revenue-card,
.route-card {
  border-radius: var(--fa-radius);
  border: 1px solid rgba(22, 119, 255, 0.1);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
}

.stat-card {
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 4px;
  background: linear-gradient(90deg, var(--fa-brand), #67c23a);
}

.stat-card :deep(.el-card__body) {
  padding: 22px 20px;
}

.stat-card :deep(.el-statistic__head) {
  margin-bottom: 12px;
  color: var(--fa-text-secondary);
  font-size: 14px;
  font-weight: 600;
}

.stat-card :deep(.el-statistic__number) {
  color: var(--fa-text);
  font-size: 32px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(240px, 0.8fr) minmax(420px, 1.2fr);
  gap: 16px;
  align-items: start;
}

.revenue-card :deep(.el-card__header),
.route-card :deep(.el-card__header) {
  color: var(--fa-text);
  font-size: 16px;
  font-weight: 700;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.revenue-card :deep(.el-card__body) {
  padding: 26px 20px;
}

.revenue-value {
  color: var(--fa-brand);
  font-size: 34px;
  font-weight: 800;
  line-height: 1.3;
  letter-spacing: 0.01em;
}

.route-table {
  border-radius: 10px;
  overflow: hidden;
}

.route-table :deep(.el-table__header th) {
  color: var(--fa-text);
  font-weight: 700;
  background: #f6faff;
}

.route-table :deep(.el-table__row) {
  height: 58px;
}

.route-table :deep(.el-table__row:hover > td) {
  background: #f8fbff;
}

.rank-badge {
  display: inline-grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  background: var(--fa-brand);
  font-size: 13px;
  font-weight: 800;
}

.airport-code {
  display: inline-block;
  min-width: 52px;
  padding: 4px 10px;
  border-radius: 999px;
  color: var(--fa-brand);
  background: rgba(22, 119, 255, 0.08);
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-align: center;
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
  border-radius: 999px;
  background: #e8f1ff;
  overflow: hidden;
}

.heat-bar {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--fa-brand), #67c23a);
}

@media (max-width: 1080px) {
  .summary-grid,
  .content-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .summary-grid,
  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
