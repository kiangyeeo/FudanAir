<script setup lang="ts">
import { computed } from 'vue'
import { Tickets } from '@element-plus/icons-vue'
import AirlineLogo from './AirlineLogo.vue'
import { formatCurrency, formatTime } from '@/utils/format'
import type { DirectFlightCandidate, NearbyFlightCandidate } from '@/types/search'

const props = defineProps<{
  candidate: DirectFlightCandidate | NearbyFlightCandidate
}>()

const emit = defineEmits<{
  select: [candidate: DirectFlightCandidate | NearbyFlightCandidate]
}>()

const seatSummary = computed(() => `经济舱 ${props.candidate.economy_left} / 头等舱 ${props.candidate.first_left}`)
</script>

<template>
  <article class="flight-card">
    <AirlineLogo :code="candidate.airline_code" :name="candidate.airline_name" :size="38" />
    <div class="time-block mono-num">
      <strong>{{ formatTime(candidate.scheduled_departure) }}</strong>
      <span>{{ candidate.dep_airport_code }}</span>
    </div>
    <div class="route-line">
      <span>{{ candidate.airline_name }} {{ candidate.flight_no }}</span>
      <span class="line"></span>
      <span>{{ seatSummary }}</span>
    </div>
    <div class="time-block mono-num">
      <strong>{{ formatTime(candidate.scheduled_arrival) }}</strong>
      <span>{{ candidate.arr_airport_code }}</span>
    </div>
    <div class="price-block">
      <div class="price mono-num">{{ formatCurrency(candidate.min_price) }}</div>
      <div class="price-detail mono-num">
        机票 {{ formatCurrency(candidate.min_ticket_price) }} + 燃油基建 {{ formatCurrency(candidate.fuel_infra_fee) }}
      </div>
      <el-button type="primary" size="small" :icon="Tickets" @click="emit('select', candidate)">预订</el-button>
    </div>
  </article>
</template>

<style scoped lang="scss">
.flight-card {
  display: grid;
  grid-template-columns: 44px 92px 1fr 92px minmax(170px, max-content);
  gap: 14px;
  align-items: center;
  min-height: 86px;
  padding: 12px 14px;
  background: var(--fa-white);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
}

.time-block {
  display: grid;
  gap: 4px;
}

.time-block strong {
  font-size: 22px;
  letter-spacing: 0;
}

.time-block span,
.route-line {
  color: var(--fa-text-secondary);
  font-size: 13px;
}

.route-line {
  display: grid;
  gap: 6px;
}

.line {
  display: block;
  height: 1px;
  background: var(--fa-border);
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

.price-detail {
  color: var(--fa-text-secondary);
  font-size: 12px;
  text-align: right;
}

@media (max-width: 760px) {
  .flight-card {
    grid-template-columns: 44px minmax(0, 1fr);
    align-items: start;
  }

  .route-line,
  .price-block {
    grid-column: 1 / -1;
  }

  .price-block {
    justify-items: start;
  }

  .price,
  .price-detail {
    text-align: left;
  }
}
</style>
