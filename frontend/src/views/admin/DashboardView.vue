<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Calendar, Tickets, TrendCharts, User } from '@element-plus/icons-vue'
import CountUp from '@/components/common/CountUp.vue'
import { adminApi } from '@/api/admin'
import type { AdminDashboard } from '@/types/admin'

const dashboard = ref<AdminDashboard | null>(null)
const loading = ref(false)

const statCards = [
  { key: 'total_orders', title: '总订单数', icon: Tickets, color: '#1677ff' },
  { key: 'today_orders', title: '今日新增订单', icon: Calendar, color: '#18b56a' },
  { key: 'total_users', title: '总用户数', icon: User, color: '#722ed1' },
  { key: 'active_users_30d', title: '活跃用户数', icon: TrendCharts, color: '#ff7a45' },
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
      <div
        v-for="(item, index) in statCards"
        :key="item.key"
        class="stat-card"
        v-motion
        :initial="{ opacity: 0, y: 16 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 360, delay: index * 70 } }"
      >
        <span class="stat-icon" :style="{ background: item.color }">
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
        <span class="revenue-label">今日成交额</span>
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
  gap: 14px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  background: var(--fa-surface);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
  box-shadow: var(--fa-shadow-1);
  transition: transform var(--fa-dur-base) var(--fa-ease), box-shadow var(--fa-dur-base) var(--fa-ease);
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--fa-shadow-2);
}

.stat-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  color: #fff;
  font-size: 22px;
}

.stat-body {
  display: grid;
  gap: 4px;
}

.stat-title {
  color: var(--fa-text-tertiary);
  font-size: 13px;
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(260px, 0.8fr) minmax(420px, 1.2fr);
  gap: 16px;
  align-items: start;
}

.revenue-card {
  display: grid;
  gap: 10px;
  padding: 26px;
  border-radius: var(--fa-radius);
  color: #fff;
  background: var(--fa-grad-brand-deep);
  box-shadow: var(--fa-shadow-2);
}

.revenue-label {
  font-size: 14px;
  opacity: 0.9;
}

.revenue-value {
  display: flex;
  align-items: baseline;
  font-size: 38px;
  font-weight: 800;
  letter-spacing: 0;
}

.revenue-value .cny {
  margin-right: 2px;
  font-size: 22px;
}

.revenue-foot {
  font-size: 12px;
  opacity: 0.78;
}

.route-card {
  border-radius: var(--fa-radius);
  border: 1px solid rgba(22, 119, 255, 0.1);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
}

.route-card :deep(.el-card__header) {
  color: var(--fa-text);
  font-size: 16px;
  font-weight: 700;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
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
  place-items: center;
  width: 28px;
  height: 28px;
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  background: var(--fa-brand);
  border-radius: 50%;
}

.airport-code {
  display: inline-block;
  min-width: 52px;
  padding: 4px 10px;
  color: var(--fa-brand);
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0;
  text-align: center;
  background: rgba(22, 119, 255, 0.08);
  border-radius: 999px;
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
  background: #e8f1ff;
  border-radius: 999px;
}

.heat-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--fa-brand), #67c23a);
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