<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { bookingApi } from '@/api/booking'
import { flightApi } from '@/api/flight'
import { passengerApi } from '@/api/passenger'
import PassengerForm from '@/components/order/PassengerForm.vue'
import { useBookingStore } from '@/stores/booking'
import { formatCurrency, formatTime } from '@/utils/format'
import type { BookingRequest, BookingSegmentSelection } from '@/types/booking'
import type { CabinClass, FareType } from '@/types/common'
import type { FlightInstance } from '@/types/flight'
import type { Passenger } from '@/types/user'

const router = useRouter()
const route = useRoute()
const bookingStore = useBookingStore()
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
      label: isTransitBooking.value ? `第 ${index + 1} 段` : '航段',
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
    ElMessage.success('订单已创建，请在 15 分钟内支付')
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
    ElMessage.warning('请选择常用乘机人')
    return
  }

  const existingIds = new Set(passengers.value.map((item) => item.id_no.trim()).filter(Boolean))
  const additions = selected.filter((item) => !existingIds.has(item.id_no))
  if (!additions.length) {
    ElMessage.warning('所选乘机人已在订单中')
    return
  }

  const current = passengers.value.length === 1 && isBlankPassenger(passengers.value[0]) ? [] : passengers.value
  passengers.value = [...current, ...additions]
  selectedSavedIds.value = []
}

function normalizePayload(): BookingRequest | null {
  const bookingSegments = selectedSegments.value
  if (!bookingSegments.length) {
    ElMessage.warning('请填写航班实例 ID')
    return null
  }

  const normalizedPassengers = passengers.value.map((item) => ({
    id_no: item.id_no.trim(),
    real_name: item.real_name.trim(),
    birth_date: item.birth_date,
  }))

  if (!normalizedPassengers.length) {
    ElMessage.warning('请至少填写一位乘机人')
    return null
  }

  const ids = new Set<string>()
  for (const passenger of normalizedPassengers) {
    if (!passenger.id_no || !passenger.real_name || !passenger.birth_date) {
      ElMessage.warning('请完整填写乘机人证件号、姓名和出生日期')
      return null
    }
    if (ids.has(passenger.id_no)) {
      ElMessage.warning(`乘机人证件号重复：${passenger.id_no}`)
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
    <section class="page-section">
      <h1 class="page-title">填写订单</h1>
      <el-form :model="form" label-position="top" class="booking-form">
        <el-form-item v-if="!isTransitBooking" label="航班实例 ID">
          <el-input v-model="form.instance_id" placeholder="如 CA1234_20260510" />
        </el-form-item>
        <el-form-item v-else label="中转航段">
          <div class="segment-tags">
            <el-tag v-for="row in priceRows" :key="row.key" type="info">
              {{ row.label }} · {{ row.segment.instance_id }}
            </el-tag>
          </div>
        </el-form-item>
        <el-form-item label="舱位">
          <el-select v-model="form.cabin_class">
            <el-option label="经济舱" value="经济舱" />
            <el-option label="头等舱" value="头等舱" />
          </el-select>
        </el-form-item>
        <el-form-item label="票价类型">
          <el-select v-model="form.fare_type">
            <el-option label="标准" value="标准" />
            <el-option label="特价" value="特价" />
          </el-select>
        </el-form-item>
      </el-form>
      <div v-if="selectedSegments.length" v-loading="detailLoading" class="price-summary">
        <h2>价格明细</h2>
        <el-table :data="priceRows" border row-key="key">
          <el-table-column prop="label" label="航段" width="90" />
          <el-table-column label="航班实例" min-width="190">
            <template #default="{ row }">
              <div>{{ row.detail?.flight_no ?? '--' }} · {{ row.segment.instance_id }}</div>
              <span class="subtle">
                {{ row.detail?.dep_airport_code ?? '--' }} → {{ row.detail?.arr_airport_code ?? '--' }}
                {{ formatTime(row.detail?.scheduled_departure) }} - {{ formatTime(row.detail?.scheduled_arrival) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="舱位票价" min-width="240">
            <template #default="{ row }">
              <div>{{ row.segment.cabin_class }} · {{ row.segment.fare_type }}</div>
              <span class="subtle mono-num">
                机票 {{ formatCurrency(row.ticketPrice) }} + 燃油基建 {{ formatCurrency(row.fuelFee) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="单人合计" width="130">
            <template #default="{ row }">
              <span class="price mono-num">{{ formatCurrency(row.actualPrice) }}</span>
            </template>
          </el-table-column>
        </el-table>
        <div class="price-total mono-num">单人行程合计 {{ formatCurrency(totalPerPassenger) }}</div>
      </div>
    </section>

    <section class="page-section">
      <div class="section-header">
        <h2>乘机人</h2>
        <div class="passenger-picker">
          <el-select
            v-model="selectedSavedIds"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            :loading="passengerLoading"
            :disabled="!savedPassengerOptions.length"
            placeholder="选择常用乘机人"
          >
            <el-option v-for="item in savedPassengerOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-button :disabled="!savedPassengerOptions.length" @click="appendSavedPassengers">带入</el-button>
        </div>
      </div>
      <PassengerForm v-model="passengers" />
      <div class="actions">
        <el-button type="primary" :loading="loading" @click="submit">提交订单</el-button>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.booking-page {
  display: grid;
  gap: 16px;
}

.booking-form {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 160px 160px;
  gap: 12px;
}

h2 {
  margin: 0;
  font-size: 16px;
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

.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.segment-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.price-summary {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.price-total {
  justify-self: end;
  color: var(--fa-text-primary);
  font-weight: 700;
}

.price {
  color: var(--fa-danger);
  font-weight: 700;
}

.subtle {
  color: var(--fa-text-secondary);
  font-size: 12px;
}

@media (max-width: 760px) {
  .booking-form,
  .passenger-picker {
    grid-template-columns: 1fr;
  }
}
</style>
