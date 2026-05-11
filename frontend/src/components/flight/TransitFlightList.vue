<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import { formatCurrency, formatDuration, formatTime } from '@/utils/format'
import type { DirectFlightCandidate, TransitCandidate } from '@/types/search'

defineProps<{
  items: TransitCandidate[]
}>()

const emit = defineEmits<{
  select: [candidate: DirectFlightCandidate]
}>()
</script>

<template>
  <section class="flight-list">
    <h2>中转方案</h2>
    <template v-if="items.length">
      <article v-for="item in items" :key="`${item.leg1.instance_id}-${item.leg2.instance_id}`" class="transit-card">
        <div class="flight-summary">
          <strong>{{ item.leg1.flight_no }} → {{ item.leg2.flight_no }}</strong>
          <p>{{ item.leg1.dep_airport_code }} {{ formatTime(item.leg1.scheduled_departure) }} / {{ item.leg2.arr_airport_code }} {{ formatTime(item.leg2.scheduled_arrival) }}</p>
        </div>
        <div class="transit-info mono-num">中转 {{ item.transit_airport }} · {{ formatDuration(item.transit_minutes) }}</div>
        <div class="price-block">
          <div class="price mono-num">{{ formatCurrency(item.total_min_price) }}</div>
          <div class="leg-actions">
            <el-button size="small" @click="emit('select', item.leg1)">订第一段</el-button>
            <el-button size="small" @click="emit('select', item.leg2)">订第二段</el-button>
          </div>
        </div>
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
  grid-template-columns: minmax(180px, 1fr) minmax(150px, max-content) minmax(160px, max-content);
  gap: 14px;
  align-items: center;
  min-width: 0;
  min-height: 86px;
  padding: 12px 14px;
  background: var(--fa-white);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
}

.flight-summary,
.transit-info,
.price-block {
  min-width: 0;
}

.flight-summary strong,
.transit-info,
p {
  overflow-wrap: anywhere;
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

.price-block {
  display: grid;
  justify-items: end;
  gap: 6px;
}

.leg-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

@media (max-width: 720px) {
  .transit-card {
    grid-template-columns: minmax(0, 1fr);
    align-items: start;
  }

  .transit-info,
  .price,
  .price-block {
    justify-items: start;
    text-align: left;
  }

  .leg-actions {
    justify-content: flex-start;
  }
}
</style>
