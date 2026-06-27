<script setup lang="ts">
import { computed } from 'vue'
import { Tickets } from '@element-plus/icons-vue'
import AirlineLogo from './AirlineLogo.vue'
import FlightPath from './FlightPath.vue'
import { formatCurrency, formatTime, minutesBetween } from '@/utils/format'
import { useAirportStore } from '@/stores/airport'
import type { DirectFlightCandidate, NearbyFlightCandidate } from '@/types/search'

const airportStore = useAirportStore()

const props = withDefaults(
  defineProps<{
    candidate: DirectFlightCandidate | NearbyFlightCandidate
    /** 列表中最低价标记 */
    lowest?: boolean
    /** 临近机场标签，如 "临近出发 · SHA" */
    nearbyTag?: string | null
  }>(),
  {
    lowest: false,
    nearbyTag: null,
  },
)

const emit = defineEmits<{
  select: [candidate: DirectFlightCandidate | NearbyFlightCandidate]
}>()

const duration = computed(() =>
  minutesBetween(props.candidate.scheduled_departure, props.candidate.scheduled_arrival),
)
const economyLow = computed(() => props.candidate.economy_left > 0 && props.candidate.economy_left <= 5)
const firstLow = computed(() => props.candidate.first_left > 0 && props.candidate.first_left <= 3)
const scarce = computed(() => economyLow.value && props.candidate.economy_left <= 3)
</script>

<template>
  <article class="flight-card is-hover-lift" :class="{ 'is-lowest': lowest }">
    <div class="ribbons">
      <span v-if="lowest" class="ribbon lowest">最低价</span>
      <span v-if="nearbyTag" class="ribbon nearby">{{ nearbyTag }}</span>
    </div>

    <div class="airline">
      <AirlineLogo :code="candidate.airline_code" :name="candidate.airline_name" :size="40" />
      <div class="airline-meta">
        <strong>{{ candidate.airline_name }}</strong>
        <span class="mono-num">{{ candidate.flight_no }}</span>
      </div>
    </div>

    <div class="time-block">
      <strong class="mono-num">{{ formatTime(candidate.scheduled_departure) }}</strong>
      <span>{{ airportStore.display(candidate.dep_airport_code) }}</span>
    </div>

    <FlightPath :duration="duration" :stops="0" class="path" />

    <div class="time-block">
      <strong class="mono-num">{{ formatTime(candidate.scheduled_arrival) }}</strong>
      <span>{{ airportStore.display(candidate.arr_airport_code) }}</span>
    </div>

    <div class="seats">
      <span class="seat-chip" :class="{ urgent: economyLow }">经济 {{ candidate.economy_left }}</span>
      <span class="seat-chip first" :class="{ urgent: firstLow }">头等 {{ candidate.first_left }}</span>
      <span v-if="scarce" class="seat-chip danger">仅剩 {{ candidate.economy_left }} 张</span>
    </div>

    <div class="price-block">
      <div class="price mono-num"><span class="cny">¥</span>{{ candidate.min_price.toFixed(0) }}</div>
      <div class="price-detail mono-num">
        机票 {{ formatCurrency(candidate.min_ticket_price) }} + 燃油基建 {{ formatCurrency(candidate.fuel_infra_fee) }}
      </div>
      <el-button type="primary" round :icon="Tickets" @click="emit('select', candidate)">预订</el-button>
    </div>
  </article>
</template>

<style scoped lang="scss">
.flight-card {
  position: relative;
  display: grid;
  grid-template-columns: 160px minmax(64px, auto) minmax(120px, 1fr) minmax(64px, auto) auto minmax(150px, max-content);
  gap: 18px;
  align-items: center;
  min-height: 92px;
  padding: 18px 20px;
  background: var(--fa-surface);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
  box-shadow: var(--fa-shadow-1);
  transition: transform var(--fa-dur-base) var(--fa-ease), box-shadow var(--fa-dur-base) var(--fa-ease),
    border-color var(--fa-dur-fast) var(--fa-ease);
}

.flight-card:hover {
  transform: translateY(-3px);
  border-color: rgba(22, 119, 255, 0.4);
  box-shadow: var(--fa-shadow-2);
}

.flight-card.is-lowest {
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
}

.ribbon.lowest {
  background: var(--fa-grad-promo);
}

.ribbon.nearby {
  background: var(--fa-brand);
}

.airline {
  display: flex;
  gap: 10px;
  align-items: center;
  min-width: 0;
}

.airline-meta {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.airline-meta strong {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.airline-meta span {
  color: var(--fa-text-tertiary);
  font-size: 12px;
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
  .flight-card {
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .airline {
    grid-column: 1 / -1;
  }

  .path {
    grid-column: 1 / -1;
  }

  .seats {
    flex-direction: row;
    flex-wrap: wrap;
    grid-column: 1 / -1;
  }

  .price-block {
    grid-column: 1 / -1;
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
