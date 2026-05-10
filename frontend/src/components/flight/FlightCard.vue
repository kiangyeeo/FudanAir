<script setup lang="ts">
import { computed } from 'vue'
import { formatCurrency, formatTime } from '@/utils/format'
import type { DirectFlightCandidate, NearbyFlightCandidate } from '@/types/search'

const props = defineProps<{
  candidate: DirectFlightCandidate | NearbyFlightCandidate
}>()

const seatSummary = computed(() => `经济舱 ${props.candidate.economy_left} / 头等舱 ${props.candidate.first_left}`)
</script>

<template>
  <article class="flight-card">
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
    <div class="price mono-num">{{ formatCurrency(candidate.min_price) }}</div>
  </article>
</template>

<style scoped lang="scss">
.flight-card {
  display: grid;
  grid-template-columns: 92px 1fr 92px 120px;
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
</style>
