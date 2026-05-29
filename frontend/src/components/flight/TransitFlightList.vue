<script setup lang="ts">
import { Tickets } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import AirlineLogo from './AirlineLogo.vue'
import { formatCurrency, formatDuration, formatTime } from '@/utils/format'
import type { TransitCandidate } from '@/types/search'

defineProps<{
  items: TransitCandidate[]
}>()

const emit = defineEmits<{
  select: [candidate: TransitCandidate]
}>()
</script>

<template>
  <section class="flight-list">
    <h2>中转方案</h2>
    <template v-if="items.length">
      <article v-for="item in items" :key="`${item.leg1.instance_id}-${item.leg2.instance_id}`" class="transit-card">
        <div class="transit-logos">
          <AirlineLogo :code="item.leg1.airline_code" :name="item.leg1.airline_name" :size="30" />
          <AirlineLogo :code="item.leg2.airline_code" :name="item.leg2.airline_name" :size="30" />
        </div>
        <div class="flight-summary">
          <strong>{{ item.leg1.flight_no }} → {{ item.leg2.flight_no }}</strong>
          <p>{{ item.leg1.dep_airport_code }} {{ formatTime(item.leg1.scheduled_departure) }} / {{ item.leg2.arr_airport_code }} {{ formatTime(item.leg2.scheduled_arrival) }}</p>
        </div>
        <div class="transit-info mono-num">中转 {{ item.transit_airport }} · {{ formatDuration(item.transit_minutes) }}</div>
        <div class="price-block">
          <div class="price mono-num">{{ formatCurrency(item.total_min_price) }}</div>
          <div class="price-detail mono-num">
            机票 {{ formatCurrency(item.total_ticket_price) }} + 燃油基建 {{ formatCurrency(item.total_fuel_infra_fee) }}
          </div>
          <el-button type="primary" size="small" :icon="Tickets" @click="emit('select', item)">预订</el-button>
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
  grid-template-columns: 50px minmax(180px, 1fr) minmax(150px, max-content) minmax(190px, max-content);
  gap: 14px;
  align-items: center;
  min-width: 0;
  min-height: 86px;
  padding: 12px 14px;
  background: var(--fa-white);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
}

.transit-logos {
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 4px;
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

.price-detail {
  color: var(--fa-text-secondary);
  font-size: 12px;
  text-align: right;
}

.price-block {
  display: grid;
  justify-items: end;
  gap: 6px;
}

@media (max-width: 720px) {
  .transit-card {
    grid-template-columns: 50px minmax(0, 1fr);
    align-items: start;
  }

  .transit-info,
  .price-block {
    grid-column: 1 / -1;
  }

  .transit-info,
  .price,
  .price-detail,
  .price-block {
    justify-items: start;
    text-align: left;
  }
}
</style>
