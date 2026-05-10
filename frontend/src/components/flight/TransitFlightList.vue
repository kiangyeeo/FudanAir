<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import { formatCurrency, formatDuration, formatTime } from '@/utils/format'
import type { TransitCandidate } from '@/types/search'

defineProps<{
  items: TransitCandidate[]
}>()
</script>

<template>
  <section class="flight-list">
    <h2>中转方案</h2>
    <template v-if="items.length">
      <article v-for="item in items" :key="`${item.leg1.instance_id}-${item.leg2.instance_id}`" class="transit-card">
        <div>
          <strong>{{ item.leg1.flight_no }} → {{ item.leg2.flight_no }}</strong>
          <p>{{ item.leg1.dep_airport_code }} {{ formatTime(item.leg1.scheduled_departure) }} / {{ item.leg2.arr_airport_code }} {{ formatTime(item.leg2.scheduled_arrival) }}</p>
        </div>
        <div class="mono-num">中转 {{ item.transit_airport }} · {{ formatDuration(item.transit_minutes) }}</div>
        <div class="price mono-num">{{ formatCurrency(item.total_min_price) }}</div>
      </article>
    </template>
    <EmptyState v-else title="暂无中转方案" description="中转方案需满足 2 至 6 小时衔接窗口。" />
  </section>
</template>

<style scoped lang="scss">
.flight-list {
  display: grid;
  gap: 10px;
}

h2 {
  margin: 0;
  font-size: 16px;
}

.transit-card {
  display: grid;
  grid-template-columns: 1fr 180px 120px;
  gap: 14px;
  align-items: center;
  min-height: 86px;
  padding: 12px 14px;
  background: var(--fa-white);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
}

p {
  margin: 6px 0 0;
  color: var(--fa-text-secondary);
  font-size: 13px;
}

.price {
  color: var(--fa-danger);
  font-size: 22px;
  font-weight: 700;
  text-align: right;
}
</style>
