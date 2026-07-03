<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { bookingApi } from '@/api/booking'
import { flightApi } from '@/api/flight'
import { passengerApi } from '@/api/passenger'
import PassengerForm from '@/components/order/PassengerForm.vue'
import FlightPath from '@/components/flight/FlightPath.vue'
import { useBookingStore } from '@/stores/booking'
import { useAirportStore } from '@/stores/airport'
import { formatCurrency, formatTime, minutesBetween } from '@/utils/format'
import { cabinClassLabel, cabinClassOptions, fareTypeLabel, fareTypeOptions } from '@/utils/labels'
import type { BookingRequest, BookingSegmentSelection } from '@/types/booking'
import type { CabinClass, FareType } from '@/types/common'
import type { FlightInstance } from '@/types/flight'
import type { Passenger } from '@/types/user'

const router = useRouter()
const route = useRoute()
const bookingStore = useBookingStore()
const airportStore = useAirportStore()
const loading = ref(false)
const passengerLoading = ref(false)
const detailLoading = ref(false)
const savedPassengers = ref<Passenger[]>([])
const selectedSavedIds = ref<string[]>([])
const passengers = ref<Passenger[]>([{ id_no: '', real_name: '', birth_date: '' }])
const transitInstanceIds = ref<string[]>([])
const segmentDetails = ref<Record<string, FlightInstance | null>>({})

const form = reactive({
  instance_id: '',
  cabin_class: '经济舱' as CabinClass,
  fare_type: '标准' as FareType,
})

const isTransitBooking = computed(() => transitInstanceIds.value.length > 1)
const selectedSegments = computed<BookingSegmentSelection[]>(() => {
  const ids = isTransitBooking.value ? transitInstanceIds.value : [form.instance_id.trim()].filter(Boolean)
  return ids.map((instanceId) => ({
    instance_id: instanceId,
    cabin_class: form.cabin_class,
    fare_type: form.fare_type,
  }))
})
const segmentKey = computed(() =>
  selectedSegments.value
    .map((item) => `${item.instance_id}:${item.cabin_class}:${item.fare_type}`)
    .join('|'),
)
const priceRows = computed(() =>
  selectedSegments.value.map((segment, index) => {
    const detail = segmentDetails.value[segment.instance_id] ?? null
    const cabinPrice = detail?.cabin_prices?.find(
      (item) => item.cabin_class === segment.cabin_class && item.fare_type === segment.fare_type,
    )
    const ticketPrice = cabinPrice?.price ?? null
    const fuelFee = detail?.fuel_infra_fee ?? null
    const actualPrice = ticketPrice !== null && fuelFee !== null ? ticketPrice + fuelFee : null
    return {
      key: `${index}-${segment.instance_id}`,
      label: isTransitBooking.value ? `Segment ${index + 1}` : 'Segment',
      segment,
      detail,
      ticketPrice,
      fuelFee,
      actualPrice,
    }
  }),
)
const totalPerPassenger = computed(() => {
  if (!priceRows.value.length || priceRows.value.some((item) => item.actualPrice === null)) {
    return null
  }
  return priceRows.value.reduce((sum, item) => sum + (item.actualPrice ?? 0), 0)
})

const savedPassengerOptions = computed(() =>
  savedPassengers.value.map((item) => ({
    label: `${item.real_name} · ${item.id_no}`,
    value: item.id_no,
  })),
)

async function submit() {
  const payload = normalizePayload()
  if (!payload) {
    return
  }

  bookingStore.setDraft(payload)
  loading.value = true
  try {
    const order = await bookingApi.createOrder(payload)
    bookingStore.setCurrentOrder(order)
    ElMessage.success('Order created. Please pay within 15 minutes')
    router.push(`/payment/${order.order_no}`)
  } finally {
    loading.value = false
  }
}

async function loadSavedPassengers() {
  passengerLoading.value = true
  try {
    savedPassengers.value = await passengerApi.list({ silentError: true })
  } catch {
    savedPassengers.value = []
  } finally {
    passengerLoading.value = false
  }
}

async function loadSegmentDetails() {
  const ids = selectedSegments.value.map((item) => item.instance_id)
  if (!ids.length) {
    segmentDetails.value = {}
    return
  }

  detailLoading.value = true
  try {
    const results = await Promise.allSettled(ids.map((id) => flightApi.getInstance(id, { silentError: true })))
    const next: Record<string, FlightInstance | null> = {}
    results.forEach((result, index) => {
      next[ids[index]] = result.status === 'fulfilled' ? result.value : null
    })
    segmentDetails.value = next
  } finally {
    detailLoading.value = false
  }
}

function appendSavedPassengers() {
  const selected = savedPassengers.value.filter((item) => selectedSavedIds.value.includes(item.id_no))
  if (!selected.length) {
    ElMessage.warning('Select saved passengers')
    return
  }

  const existingIds = new Set(passengers.value.map((item) => item.id_no.trim()).filter(Boolean))
  const additions = selected.filter((item) => !existingIds.has(item.id_no))
  if (!additions.length) {
    ElMessage.warning('Selected passengers are already in the order')
    return
  }

  const current = passengers.value.length === 1 && isBlankPassenger(passengers.value[0]) ? [] : passengers.value
  passengers.value = [...current, ...additions]
  selectedSavedIds.value = []
}

function normalizePayload(): BookingRequest | null {
  const bookingSegments = selectedSegments.value
  if (!bookingSegments.length) {
    ElMessage.warning('Enter a flight instance ID')
    return null
  }

  const normalizedPassengers = passengers.value.map((item) => ({
    id_no: item.id_no.trim(),
    real_name: item.real_name.trim(),
    birth_date: item.birth_date,
  }))

  if (!normalizedPassengers.length) {
    ElMessage.warning('Enter at least one passenger')
    return null
  }

  const ids = new Set<string>()
  for (const passenger of normalizedPassengers) {
    if (!passenger.id_no || !passenger.real_name || !passenger.birth_date) {
      ElMessage.warning('Complete passenger ID number, name, and date of birth')
      return null
    }
    if (ids.has(passenger.id_no)) {
      ElMessage.warning(`Duplicate passenger ID number: ${passenger.id_no}`)
      return null
    }
    ids.add(passenger.id_no)
  }

  const basePayload = {
    passengers: normalizedPassengers,
  }
  if (bookingSegments.length === 1) {
    return {
      ...bookingSegments[0],
      ...basePayload,
    }
  }
  return {
    segments: bookingSegments,
    ...basePayload,
  }
}

function isBlankPassenger(passenger: Passenger) {
  return !passenger.id_no && !passenger.real_name && !passenger.birth_date
}

function queryText(key: string): string | null {
  const value = route.query[key]
  if (Array.isArray(value)) {
    return value[0] ?? null
  }
  return value ?? null
}

function cabinClass(value: string | null): CabinClass | null {
  return value === '经济舱' || value === '头等舱' ? value : null
}

function fareType(value: string | null): FareType | null {
  return value === '标准' || value === '特价' ? value : null
}

watch(
  () => ({ segmentKey: segmentKey.value, passengers: passengers.value }),
  () => {
    bookingStore.setDraft(currentDraft())
  },
  { deep: true },
)

watch(segmentKey, () => {
  void loadSegmentDetails()
})

onMounted(() => {
  void airportStore.ensureLoaded()
  const instanceId = queryText('instance_id')
  const routeSegments = queryText('segments')
    ?.split(',')
    .map((item) => item.trim())
    .filter(Boolean)
  const draft = bookingStore.draft
  const draftSegments = draft?.segments?.map((item) => item.instance_id) ?? []
  const cabin = cabinClass(queryText('cabin_class'))
  const fare = fareType(queryText('fare_type'))

  transitInstanceIds.value = instanceId ? [] : routeSegments?.length ? routeSegments : draftSegments
  form.instance_id = instanceId ?? routeSegments?.[0] ?? draft?.instance_id ?? draftSegments[0] ?? ''
  form.cabin_class = cabin ?? draft?.cabin_class ?? draft?.segments?.[0]?.cabin_class ?? '经济舱'
  form.fare_type = fare ?? draft?.fare_type ?? draft?.segments?.[0]?.fare_type ?? '标准'
  passengers.value = draft?.passengers?.length ? draft.passengers : passengers.value
  bookingStore.setDraft(currentDraft())
  void loadSegmentDetails()
  void loadSavedPassengers()
})

function currentDraft(): BookingRequest | null {
  const draft = { passengers: passengers.value }
  if (selectedSegments.value.length > 1) {
    return { segments: selectedSegments.value, ...draft }
  }
  return {
    instance_id: form.instance_id,
    cabin_class: form.cabin_class,
    fare_type: form.fare_type,
    ...draft,
  }
}
</script>

<template>
  <div class="page-shell booking-page">
    <div class="booking-main">
      <section class="page-section">
        <h1 class="page-title">Create Order</h1>
        <el-form :model="form" label-position="top" class="booking-form">
          <el-form-item v-if="!isTransitBooking" label="Flight Instance ID">
            <el-input v-model="form.instance_id" placeholder="e.g. CA1234_20260510" />
          </el-form-item>
          <el-form-item v-else label="Transfer Segments">
            <div class="segment-tags">
              <el-tag v-for="row in priceRows" :key="row.key" type="info">
                {{ row.label }} · {{ row.segment.instance_id }}
              </el-tag>
            </div>
          </el-form-item>
          <el-form-item label="Cabin">
            <el-select v-model="form.cabin_class">
              <el-option v-for="item in cabinClassOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="Fare Type">
            <el-select v-model="form.fare_type">
              <el-option v-for="item in fareTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-form>
      </section>

      <section class="page-section">
        <div class="section-header">
          <h2>Passengers</h2>
          <div class="passenger-picker">
            <el-select
              v-model="selectedSavedIds"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              :loading="passengerLoading"
              :disabled="!savedPassengerOptions.length"
              placeholder="Select saved passengers"
            >
              <el-option v-for="item in savedPassengerOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <el-button :disabled="!savedPassengerOptions.length" @click="appendSavedPassengers">Add</el-button>
          </div>
        </div>
        <PassengerForm v-model="passengers" />
      </section>
    </div>

    <aside class="booking-aside">
      <section v-loading="detailLoading" class="page-section summary-card">
        <h2 class="summary-title">Order Summary</h2>
        <div v-if="selectedSegments.length" class="seg-list">
          <div v-for="row in priceRows" :key="row.key" class="seg-item">
            <div class="seg-head">
              <span class="seg-label">{{ row.label }}</span>
              <span class="seg-flight mono-num">{{ row.detail?.flight_no ?? '--' }}</span>
            </div>
            <div class="seg-route mono-num">
              <div class="endpoint">
                <strong>{{ formatTime(row.detail?.scheduled_departure) }}</strong>
                <span>{{ airportStore.display(row.detail?.dep_airport_code) }}</span>
              </div>
              <FlightPath
                :duration="minutesBetween(row.detail?.scheduled_departure, row.detail?.scheduled_arrival)"
                class="seg-path"
                compact
              />
              <div class="endpoint">
                <strong>{{ formatTime(row.detail?.scheduled_arrival) }}</strong>
                <span>{{ airportStore.display(row.detail?.arr_airport_code) }}</span>
              </div>
            </div>
            <div class="seg-fee">
              <span class="subtle">{{ cabinClassLabel(row.segment.cabin_class) }} · {{ fareTypeLabel(row.segment.fare_type) }}</span>
              <span class="price mono-num">{{ formatCurrency(row.actualPrice) }}</span>
            </div>
            <div class="subtle mono-num seg-breakdown">
              Ticket {{ formatCurrency(row.ticketPrice) }} + Fuel & airport fee {{ formatCurrency(row.fuelFee) }}
            </div>
          </div>
        </div>
        <p v-else class="subtle">Select a flight to view price details.</p>

        <div class="summary-foot">
          <div class="foot-row">
            <span>Per Passenger</span>
            <span class="mono-num">{{ formatCurrency(totalPerPassenger) }}</span>
          </div>
          <div class="foot-row">
            <span>Passengers</span>
            <span class="mono-num">× {{ passengers.length }}</span>
          </div>
          <div class="foot-row total">
            <span>Estimated Total</span>
            <span class="price mono-num">
              {{ totalPerPassenger != null ? formatCurrency(totalPerPassenger * passengers.length) : '¥--' }}
            </span>
          </div>
          <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submit">Submit Order</el-button>
        </div>
      </section>
    </aside>
  </div>
</template>

<style scoped lang="scss">
.booking-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
  align-items: start;
  padding: 20px 0 8px;
}

.booking-main {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.booking-aside {
  position: sticky;
  top: calc(var(--fa-header-height) + 16px);
}

.booking-form {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 160px 160px;
  gap: 12px;
}

h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

.section-header {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.passenger-picker {
  display: grid;
  grid-template-columns: minmax(220px, 320px) auto;
  gap: 8px;
}

.segment-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* ---------- 摘要卡 ---------- */
.summary-card {
  display: grid;
  gap: 16px;
}

.summary-title {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--fa-border);
}

.seg-list {
  display: grid;
  gap: 16px;
}

.seg-item {
  display: grid;
  gap: 8px;
}

.seg-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.seg-label {
  padding: 1px 8px;
  border-radius: var(--fa-radius-pill);
  background: var(--fa-brand-soft);
  color: var(--fa-brand);
  font-size: 12px;
  font-weight: 600;
}

.seg-flight {
  color: var(--fa-text-tertiary);
  font-size: 12px;
}

.seg-route {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px;
  align-items: center;
}

.endpoint {
  display: grid;
  text-align: center;
}

.endpoint strong {
  font-size: 17px;
  font-weight: 700;
}

.endpoint span {
  color: var(--fa-text-secondary);
  font-size: 12px;
}

.seg-fee {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.seg-breakdown {
  margin-top: -2px;
}

.summary-foot {
  display: grid;
  gap: 8px;
  padding-top: 14px;
  border-top: 1px dashed var(--fa-border);
}

.foot-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  color: var(--fa-text-secondary);
  font-size: 14px;
}

.foot-row.total {
  margin-top: 2px;
  color: var(--fa-text);
  font-weight: 700;
}

.foot-row.total .price {
  font-size: 24px;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}

.price {
  color: var(--fa-promo);
  font-weight: 800;
}

.subtle {
  color: var(--fa-text-secondary);
  font-size: 12px;
}

@media (max-width: 960px) {
  .booking-page {
    grid-template-columns: 1fr;
  }

  .booking-aside {
    position: static;
  }
}

@media (max-width: 760px) {
  .booking-form,
  .passenger-picker {
    grid-template-columns: 1fr;
  }
}
</style>
