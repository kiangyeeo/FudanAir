<script setup lang="ts">
import { computed } from 'vue'
import { Tickets } from '@element-plus/icons-vue'
import AirlineLogo from './AirlineLogo.vue'
import FlightPath from './FlightPath.vue'
import { formatCurrency, formatDuration, formatTime, withTerminal } from '@/utils/format'
import { useAirportStore } from '@/stores/airport'
import { useFlightMetaStore } from '@/stores/flightMeta'
import type { TransitCandidate } from '@/types/search'

const airportStore = useAirportStore()
const flightMeta = useFlightMetaStore()

const props = withDefaults(
  defineProps<{
    candidate: TransitCandidate
    /** 列表中最低价标记 */
    lowest?: boolean
  }>(),
  { lowest: false },
)

const emit = defineEmits<{
  select: [candidate: TransitCandidate]
}>()

// 联程可售量取两段的瓶颈(较小者)
const economyLeft = computed(() => Math.min(props.candidate.leg1.economy_left, props.candidate.leg2.economy_left))
const firstLeft = computed(() => Math.min(props.candidate.leg1.first_left, props.candidate.leg2.first_left))
const economyLow = computed(() => economyLeft.value > 0 && economyLeft.value <= 5)
const firstLow = computed(() => firstLeft.value > 0 && firstLeft.value <= 3)
const scarce = computed(() => economyLow.value && economyLeft.value <= 3)

function transitLabel(item: TransitCandidate) {
  return `中转 ${airportStore.display(item.transit_airport)} · ${formatDuration(item.transit_minutes)}`
}
</script>

<template>
  <article class="transit-card is-hover-lift" :class="{ 'is-lowest': lowest }">
    <div class="ribbons">
      <span v-if="lowest" class="ribbon lowest">最低价</span>
      <span class="ribbon transit">中转</span>
    </div>

    <div class="airline">
      <div class="logos">
        <AirlineLogo :code="candidate.leg1.airline_code" :name="candidate.leg1.airline_name" :size="28" />
        <AirlineLogo :code="candidate.leg2.airline_code" :name="candidate.leg2.airline_name" :size="28" />
      </div>
      <div class="flight-lines">
        <span class="flight-nos mono-num">{{ candidate.leg1.flight_no }} / {{ candidate.leg2.flight_no }}</span>
        <span class="aircraft-model mono-num">{{ candidate.leg1.aircraft_model }} / {{ candidate.leg2.aircraft_model }}</span>
      </div>
    </div>

    <div class="time-block">
      <strong class="mono-num">{{ formatTime(candidate.leg1.scheduled_departure) }}</strong>
      <span>{{ withTerminal(airportStore.display(candidate.leg1.dep_airport_code), flightMeta.depTerminal(candidate.leg1.flight_no)) }}</span>
    </div>

    <FlightPath
      :duration="candidate.total_duration_minutes"
      :stops="1"
      :stop-label="transitLabel(candidate)"
      class="path"
    />

    <div class="time-block">
      <strong class="mono-num">{{ formatTime(candidate.leg2.scheduled_arrival) }}</strong>
      <span>{{ withTerminal(airportStore.display(candidate.leg2.arr_airport_code), flightMeta.arrTerminal(candidate.leg2.flight_no)) }}</span>
    </div>

    <div class="seats">
      <span class="seat-chip" :class="{ urgent: economyLow }">经济 {{ economyLeft }}</span>
      <span class="seat-chip first" :class="{ urgent: firstLow }">头等 {{ firstLeft }}</span>
      <span v-if="scarce" class="seat-chip danger">仅剩 {{ economyLeft }} 张</span>
    </div>

    <div class="price-block">
      <div class="price mono-num"><span class="cny">¥</span>{{ candidate.total_min_price.toFixed(0) }}</div>
      <div class="price-detail mono-num">
        {{ candidate.leg1.min_cabin_class }} / {{ candidate.leg1.min_fare_type }} / 机票 {{ formatCurrency(candidate.total_ticket_price) }} + 燃油基建 {{ formatCurrency(candidate.total_fuel_infra_fee) }}
      </div>
      <el-button type="primary" round :icon="Tickets" @click="emit('select', candidate)">预订</el-button>
    </div>
  </article>
</template>

<style scoped lang="scss">
.transit-card {
  position: relative;
  display: grid;
  grid-template-columns: 160px minmax(64px, auto) minmax(120px, 1fr) minmax(64px, auto) auto minmax(150px, max-content);
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

.ribbons {
  position: absolute;
  top: -1px;
  left: 16px;
  display: flex;
  gap: 6px;
}

.ribbon {
  padding: 2px 10px;
  border-radius: 0 0 8px 8px;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
}

.ribbon.lowest {
  background: var(--fa-grad-promo);
}

.ribbon.transit {
  background: #722ed1;
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
  font-size: 30px;
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

.seats {
  display: flex;
  flex-direction: column;
  gap: 5px;
  align-items: flex-start;
}

.seat-chip {
  padding: 1px 9px;
  border-radius: var(--fa-radius-pill);
  background: var(--fa-surface-2);
  color: var(--fa-text-secondary);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.seat-chip.first {
  background: var(--fa-cabin-first-soft);
  color: var(--fa-cabin-first);
}

.seat-chip.urgent {
  background: var(--fa-warning-soft);
  color: #b7791f;
}

.seat-chip.danger {
  background: var(--fa-promo-soft);
  color: var(--fa-promo);
}

.price-block {
  display: grid;
  justify-items: end;
  gap: 6px;
}

.price {
  color: var(--fa-promo);
  font-size: 26px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.02em;
}

.price .cny {
  font-size: 16px;
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

  .seats {
    flex-direction: row;
    flex-wrap: wrap;
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
