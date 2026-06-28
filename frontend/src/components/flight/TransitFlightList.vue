<script setup lang="ts">
import { computed } from 'vue'
import { Tickets } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import AirlineLogo from './AirlineLogo.vue'
import FlightPath from './FlightPath.vue'
import { formatCurrency, formatDuration, formatTime, withTerminal } from '@/utils/format'
import { useAirportStore } from '@/stores/airport'
import { useFlightMetaStore } from '@/stores/flightMeta'
import type { TransitCandidate } from '@/types/search'

const airportStore = useAirportStore()
const flightMeta = useFlightMetaStore()

const props = defineProps<{
  items: TransitCandidate[]
}>()

const emit = defineEmits<{
  select: [candidate: TransitCandidate]
}>()

const lowestKey = computed(() => {
  if (!props.items.length) {
    return null
  }
  const best = props.items.reduce((min, item) => (item.total_min_price < min.total_min_price ? item : min))
  return `${best.leg1.instance_id}-${best.leg2.instance_id}`
})

function transitLabel(item: TransitCandidate) {
  return `中转 ${airportStore.display(item.transit_airport)} · ${formatDuration(item.transit_minutes)}`
}
</script>

<template>
  <section class="flight-list">
    <header class="list-head">
      <span class="dot" />
      <h2>中转方案</h2>
      <span class="count">{{ items.length }} 个方案</span>
    </header>
    <template v-if="items.length">
      <article
        v-for="(item, index) in items"
        :key="`${item.leg1.instance_id}-${item.leg2.instance_id}`"
        class="transit-card"
        :class="{ 'is-lowest': `${item.leg1.instance_id}-${item.leg2.instance_id}` === lowestKey }"
        v-motion
        :initial="{ opacity: 0, y: 14 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 320, delay: index * 55 } }"
      >
        <span
          v-if="`${item.leg1.instance_id}-${item.leg2.instance_id}` === lowestKey"
          class="ribbon"
        >最低价</span>

        <div class="airline">
          <div class="logos">
            <AirlineLogo :code="item.leg1.airline_code" :name="item.leg1.airline_name" :size="28" />
            <AirlineLogo :code="item.leg2.airline_code" :name="item.leg2.airline_name" :size="28" />
          </div>
          <div class="flight-lines">
            <span class="flight-nos mono-num">{{ item.leg1.flight_no }} / {{ item.leg2.flight_no }}</span>
            <span class="aircraft-model mono-num">{{ item.leg1.aircraft_model }} / {{ item.leg2.aircraft_model }}</span>
          </div>
        </div>

        <div class="time-block">
          <strong class="mono-num">{{ formatTime(item.leg1.scheduled_departure) }}</strong>
          <span>{{ withTerminal(airportStore.display(item.leg1.dep_airport_code), flightMeta.depTerminal(item.leg1.flight_no)) }}</span>
        </div>

        <FlightPath
          :duration="item.total_duration_minutes"
          :stops="1"
          :stop-label="transitLabel(item)"
          class="path"
        />

        <div class="time-block">
          <strong class="mono-num">{{ formatTime(item.leg2.scheduled_arrival) }}</strong>
          <span>{{ withTerminal(airportStore.display(item.leg2.arr_airport_code), flightMeta.arrTerminal(item.leg2.flight_no)) }}</span>
        </div>

        <div class="price-block">
          <div class="price mono-num"><span class="cny">¥</span>{{ item.total_min_price.toFixed(0) }}</div>
          <div class="price-detail mono-num">
            机票 {{ formatCurrency(item.total_ticket_price) }} + 燃油基建 {{ formatCurrency(item.total_fuel_infra_fee) }}
          </div>
          <el-button type="primary" round :icon="Tickets" @click="emit('select', item)">预订</el-button>
        </div>
      </article>
    </template>
    <EmptyState v-else title="暂无中转方案" description="中转方案需满足 2 至 6 小时衔接窗口。" />
  </section>
</template>

<style scoped lang="scss">
.flight-list {
  display: grid;
  gap: 12px;
}

.list-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.list-head h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #722ed1;
}

.count {
  color: var(--fa-text-tertiary);
  font-size: 13px;
}

.transit-card {
  position: relative;
  display: grid;
  grid-template-columns: 140px minmax(64px, auto) minmax(160px, 1fr) minmax(64px, auto) minmax(150px, max-content);
  gap: 18px;
  align-items: center;
  min-width: 0;
  min-height: 92px;
  padding: 18px 20px;
  background: var(--fa-surface);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
  box-shadow: var(--fa-shadow-1);
  transition: transform var(--fa-dur-base) var(--fa-ease), box-shadow var(--fa-dur-base) var(--fa-ease),
    border-color var(--fa-dur-fast) var(--fa-ease);
}

.transit-card:hover {
  transform: translateY(-3px);
  border-color: rgba(114, 46, 209, 0.4);
  box-shadow: var(--fa-shadow-2);
}

.transit-card.is-lowest {
  border-color: rgba(24, 181, 106, 0.5);
}

.ribbon {
  position: absolute;
  top: -1px;
  left: 16px;
  padding: 2px 10px;
  border-radius: 0 0 8px 8px;
  background: var(--fa-grad-promo);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
}

.airline {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.logos {
  display: inline-flex;
  gap: 6px;
}

.flight-lines {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.flight-nos {
  color: var(--fa-text-tertiary);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.aircraft-model {
  color: var(--fa-text-secondary);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.time-block {
  display: grid;
  gap: 3px;
  text-align: center;
}

.time-block strong {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.time-block span {
  color: var(--fa-text-secondary);
  font-size: 14px;
  white-space: nowrap;
}

.path {
  align-self: center;
}

.price-block {
  display: grid;
  justify-items: end;
  gap: 6px;
}

.price {
  color: var(--fa-promo);
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.02em;
}

.price .cny {
  font-size: 15px;
  font-weight: 700;
  margin-right: 1px;
}

.price-detail {
  color: var(--fa-text-tertiary);
  font-size: 12px;
  text-align: right;
}

@media (max-width: 860px) {
  .transit-card {
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .airline,
  .path,
  .price-block {
    grid-column: 1 / -1;
  }

  .price-block {
    justify-items: stretch;
  }

  .price-detail {
    text-align: left;
  }

  .price-block :deep(.el-button) {
    width: 100%;
  }
}
</style>
