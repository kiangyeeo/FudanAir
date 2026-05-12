<script setup lang="ts">
import { onMounted, ref } from 'vue'
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
          :data="dashboard?.top_routes ?? []"
          empty-text="暂无今日成交航线"
          border
        >
          <el-table-column label="排名" type="index" width="80" />
          <el-table-column label="出发机场" prop="dep_airport_code" min-width="120" />
          <el-table-column label="到达机场" prop="arr_airport_code" min-width="120" />
          <el-table-column label="订单数" prop="order_count" min-width="100" />
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
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(240px, 0.8fr) minmax(420px, 1.2fr);
  gap: 16px;
  align-items: start;
}

.revenue-value {
  color: var(--fa-brand);
  font-size: 30px;
  font-weight: 700;
  line-height: 1.3;
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
