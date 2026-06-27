<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Tickets, Calendar, User, TrendCharts } from '@element-plus/icons-vue'
import CountUp from '@/components/common/CountUp.vue'
import EmptyState from '@/components/common/EmptyState.vue'
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
const maxRouteCount = computed(() => Math.max(1, ...topRoutes.value.map((item) => item.order_count)))

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

      <div class="route-card page-section">
        <header class="route-head">
          <h2>今日热门航线 Top 5</h2>
          <span class="fa-chip">按订单数排序</span>
        </header>
        <div v-if="topRoutes.length" class="route-list">
          <div v-for="(route, index) in topRoutes" :key="`${route.dep_airport_code}-${route.arr_airport_code}`" class="route-row">
            <span class="rank" :class="{ top: index === 0 }">{{ index + 1 }}</span>
            <span class="route-name mono-num">{{ route.dep_airport_code }} → {{ route.arr_airport_code }}</span>
            <div class="route-bar">
              <span
                class="route-bar-fill"
                :style="{ width: `${(route.order_count / maxRouteCount) * 100}%` }"
              />
            </div>
            <span class="route-count mono-num">{{ route.order_count }}</span>
          </div>
        </div>
        <EmptyState v-else title="暂无今日成交航线" description="今日还没有已支付的订单。" />
      </div>
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
  letter-spacing: -0.02em;
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
  letter-spacing: -0.02em;
}

.revenue-value .cny {
  font-size: 22px;
  margin-right: 2px;
}

.revenue-foot {
  font-size: 12px;
  opacity: 0.78;
}

.route-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.route-head h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

.route-list {
  display: grid;
  gap: 14px;
}

.route-row {
  display: grid;
  grid-template-columns: 28px 130px 1fr 40px;
  gap: 12px;
  align-items: center;
}

.rank {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 8px;
  background: var(--fa-surface-2);
  color: var(--fa-text-secondary);
  font-size: 13px;
  font-weight: 700;
}

.rank.top {
  background: var(--fa-grad-promo);
  color: #fff;
}

.route-name {
  font-size: 14px;
  font-weight: 600;
}

.route-bar {
  height: 10px;
  border-radius: var(--fa-radius-pill);
  background: var(--fa-surface-2);
  overflow: hidden;
}

.route-bar-fill {
  display: block;
  height: 100%;
  border-radius: var(--fa-radius-pill);
  background: var(--fa-grad-brand);
  transition: width var(--fa-dur-slow) var(--fa-ease-out);
}

.route-count {
  text-align: right;
  font-weight: 700;
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
