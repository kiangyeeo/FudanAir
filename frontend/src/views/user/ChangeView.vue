<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Back, Calendar, Check, Right, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { flightApi } from '@/api/flight'
import { orderApi } from '@/api/order'
import { refundApi } from '@/api/refund'
import { searchApi } from '@/api/search'
import AirlineLogo from '@/components/flight/AirlineLogo.vue'
import FlightPath from '@/components/flight/FlightPath.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { formatCurrency, formatDate, formatTime, minutesBetween } from '@/utils/format'
import { cabinClassLabel, fareTypeLabel, instanceStatusLabel, refundTierLabel, ticketStatusLabel } from '@/utils/labels'
import type { CabinPrice, FlightInstance } from '@/types/flight'
import type { OrderDetail, OrderTicket } from '@/types/order'
import type { ChangeRequest, ChangeTicketResponse, RefundQuote } from '@/types/refund'
import type { DirectFlightCandidate, FlightSearchRequest, NearbyFlightCandidate } from '@/types/search'

type ChangeCandidate = DirectFlightCandidate | NearbyFlightCandidate

interface CabinPriceChoice extends CabinPrice {
  key: string
  actual_price: number
}

const BOOKABLE_INSTANCE_STATUS = '可订'

const route = useRoute()
const router = useRouter()
const orderNo = ref('')
const originalTicket = ref<OrderTicket | null>(null)
const originalLoading = ref(false)
const searchLoading = ref(false)
const detailLoading = ref(false)
const quoteLoading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const candidates = ref<ChangeCandidate[]>([])
const selectedCandidate = ref<ChangeCandidate | null>(null)
const selectedInstance = ref<FlightInstance | null>(null)
const selectedPriceKey = ref('')
const quote = ref<RefundQuote | null>(null)
const result = ref<ChangeTicketResponse | null>(null)

const form = reactive<ChangeRequest>({
  ticket_no: '',
  new_instance_id: '',
  new_cabin_class: '经济舱',
  new_fare_type: '标准',
})

// 出发/到达城市来自原客票，锁定不可更改；仅日期可改
const searchForm = reactive({
  dep_city: '',
  arr_city: '',
  flight_date: '',
})

const normalizedTicketNo = computed(() => form.ticket_no.trim())
const cabinPriceChoices = computed<CabinPriceChoice[]>(() => {
  const fuelFee = selectedInstance.value?.fuel_infra_fee ?? 0
  return (selectedInstance.value?.cabin_prices ?? [])
    .filter((item) => item.available_seats > 0)
    .map((item) => ({
      ...item,
      key: `${item.cabin_class}|${item.fare_type}`,
      actual_price: item.price + fuelFee,
    }))
})
const quoteMatches = computed(() =>
  Boolean(
    quote.value?.ticket_no === normalizedTicketNo.value &&
      quote.value?.op_type === 'change' &&
      form.new_instance_id &&
      form.new_cabin_class &&
      form.new_fare_type,
  ),
)
const settlementLabel = computed(() => ((quote.value?.amount_user_pays ?? 0) >= 0 ? 'Amount Due' : 'Refundable'))
const canSubmit = computed(() => Boolean(quote.value && quoteMatches.value && !result.value))

async function loadOriginalTicket() {
  if (!orderNo.value) {
    return
  }

  originalLoading.value = true
  try {
    const detail: OrderDetail = await orderApi.getDetail(orderNo.value)
    originalTicket.value = detail.tickets.find((item) => item.ticket_no === normalizedTicketNo.value) ?? null
    if (!originalTicket.value) {
      ElMessage.warning('Ticket not found in this order')
      return
    }
    await fillSearchCities(originalTicket.value)
  } catch {
    ElMessage.warning('Could not autofill change search criteria')
  } finally {
    originalLoading.value = false
  }
}

async function fillSearchCities(ticket: OrderTicket) {
  searchForm.flight_date = ticket.flight_date
  const [depAirport, arrAirport] = await Promise.all([
    flightApi.getAirport(ticket.dep_airport_code),
    flightApi.getAirport(ticket.arr_airport_code),
  ])
  searchForm.dep_city = depAirport.city_name
  searchForm.arr_city = arrAirport.city_name
}

function openSearchDialog() {
  if (!searchForm.dep_city || !searchForm.arr_city) {
    ElMessage.warning('Original route cities are unavailable')
    return
  }
  if (!searchForm.flight_date) {
    ElMessage.warning('Select a target date')
    return
  }
  dialogVisible.value = true
  void runSearch()
}

async function runSearch() {
  const payload = searchPayload()
  if (!payload) {
    return
  }

  candidates.value = []
  searchLoading.value = true
  try {
    const data = await searchApi.searchFlights(payload)
    // 约束：改签后必须仍从原出发城市出发、到达原到达城市，故只取同城直飞结果，
    // 不纳入 nearby（临近机场，可能位于其他城市）。
    candidates.value = data.direct
  } finally {
    searchLoading.value = false
  }
}

async function onPickCandidate(candidate: ChangeCandidate) {
  await selectCandidate(candidate)
  if (selectedInstance.value) {
    dialogVisible.value = false
  }
}

async function selectCandidate(candidate: ChangeCandidate) {
  selectedCandidate.value = candidate
  form.new_instance_id = candidate.instance_id
  selectedInstance.value = null
  selectedPriceKey.value = ''
  quote.value = null
  result.value = null

  detailLoading.value = true
  try {
    selectedInstance.value = await flightApi.getInstance(candidate.instance_id)
    if (!isChangeTargetBookable(selectedInstance.value)) {
      clearSelectedTarget()
      return
    }
    const first = cabinPriceChoices.value[0]
    if (!first) {
      ElMessage.warning('No available cabin fares for this flight')
      return
    }
    await selectCabinPrice(first)
  } finally {
    detailLoading.value = false
  }
}

async function selectCabinPrice(choice: CabinPriceChoice) {
  selectedPriceKey.value = choice.key
  form.new_cabin_class = choice.cabin_class
  form.new_fare_type = choice.fare_type
  await loadQuote()
}

async function loadQuote() {
  if (!validateQuoteParams()) {
    return
  }

  quoteLoading.value = true
  result.value = null
  try {
    quote.value = await refundApi.quote({
      ticket_no: normalizedTicketNo.value,
      op_type: 'change',
      new_instance_id: form.new_instance_id,
      new_cabin_class: form.new_cabin_class,
      new_fare_type: form.new_fare_type,
    })
  } finally {
    quoteLoading.value = false
  }
}

async function submit() {
  if (!canSubmit.value || !quote.value) {
    ElMessage.warning('Calculate change fees first')
    return
  }

  try {
    await ElMessageBox.confirm(confirmText(), 'Confirm Change', {
      confirmButtonText: 'Confirm Change',
      cancelButtonText: 'Cancel',
      type: 'warning',
    })
  } catch {
    return
  }

  submitLoading.value = true
  try {
    result.value = await refundApi.change({ ...form, ticket_no: normalizedTicketNo.value })
    ElMessage.success('Change submitted')
  } finally {
    submitLoading.value = false
  }
}

function searchPayload(): FlightSearchRequest | null {
  const depCity = searchForm.dep_city.trim()
  const arrCity = searchForm.arr_city.trim()
  if (!depCity || !arrCity || !searchForm.flight_date) {
    ElMessage.warning('Select a target date')
    return null
  }
  return {
    dep_city: depCity,
    arr_city: arrCity,
    flight_date: searchForm.flight_date,
    filters: { include_stopover: false },
    sort: { field: 'departure', order: 'asc' },
  }
}

function validateQuoteParams() {
  if (!normalizedTicketNo.value) {
    ElMessage.warning('Missing original ticket number')
    return false
  }
  if (!form.new_instance_id || !form.new_cabin_class || !form.new_fare_type) {
    ElMessage.warning('Select a new flight and fare')
    return false
  }
  return true
}

function clearSelectedTarget() {
  selectedCandidate.value = null
  selectedInstance.value = null
  selectedPriceKey.value = ''
  form.new_instance_id = ''
  quote.value = null
  result.value = null
}

function isChangeTargetBookable(instance: FlightInstance) {
  if (instance.status !== BOOKABLE_INSTANCE_STATUS) {
    ElMessage.warning(`The selected instance is ${instanceStatusLabel(instance.status)} and cannot be selected for change`)
    return false
  }
  if (isDeparted(instance)) {
    ElMessage.warning('This flight has departed and cannot be selected')
    return false
  }
  return true
}

function isDeparted(instance: FlightInstance) {
  if (!instance.scheduled_departure) {
    return false
  }
  const departureAt = new Date(`${instance.flight_date}T${instance.scheduled_departure.slice(0, 8)}`)
  return Number.isFinite(departureAt.getTime()) && departureAt.getTime() <= Date.now()
}

function backToOrder() {
  if (orderNo.value) {
    router.push({ name: 'order-detail', params: { orderNo: orderNo.value } })
    return
  }
  router.push({ name: 'orders' })
}

function confirmText() {
  const amount = quote.value?.amount_user_pays ?? 0
  return `Change ${normalizedTicketNo.value} to ${form.new_instance_id}? ${settlementLabel.value}: ${formatCurrency(Math.abs(amount))}.`
}

function feeRateText(rate?: number) {
  if (rate === undefined || Number.isNaN(rate)) {
    return '--'
  }
  return `${(rate * 100).toFixed(0)}%`
}

function formatSignedCurrency(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '¥--'
  }
  const sign = value > 0 ? '+' : value < 0 ? '-' : ''
  return `${sign}${formatCurrency(Math.abs(value))}`
}

function queryText(key: string): string | null {
  const value = route.query[key]
  if (Array.isArray(value)) {
    return value[0] ?? null
  }
  return value ?? null
}

watch(
  () => form.ticket_no,
  () => {
    quote.value = null
    result.value = null
  },
)

onMounted(() => {
  form.ticket_no = queryText('ticket_no') ?? ''
  orderNo.value = queryText('order_no') ?? ''
  void loadOriginalTicket()
})
</script>

<template>
  <div class="page-shell change-page">
    <section v-loading="originalLoading" class="page-section">
      <div class="page-heading">
        <div>
          <h1 class="page-title">Change Flight</h1>
          <span>Departure and arrival cities stay the same. Change the travel date and select a new flight.</span>
        </div>
        <el-button v-if="orderNo" :icon="Back" @click="backToOrder">Back to Order</el-button>
      </div>

      <el-descriptions v-if="originalTicket" :column="3" border class="original-ticket">
        <el-descriptions-item label="Original Ticket">{{ originalTicket.ticket_no }}</el-descriptions-item>
        <el-descriptions-item label="Passenger">{{ originalTicket.passenger.real_name }}</el-descriptions-item>
        <el-descriptions-item label="Status">
          <el-tag :type="originalTicket.status === '有效' ? 'success' : 'info'">{{ ticketStatusLabel(originalTicket.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Original Flight">
          {{ originalTicket.flight_no }} · {{ originalTicket.instance_id }}
        </el-descriptions-item>
        <el-descriptions-item label="Route">
          {{ originalTicket.dep_airport_code }} → {{ originalTicket.arr_airport_code }}
        </el-descriptions-item>
        <el-descriptions-item label="Date & Time">
          {{ formatDate(originalTicket.flight_date) }} {{ formatTime(originalTicket.scheduled_departure) }} - {{ formatTime(originalTicket.scheduled_arrival) }}
        </el-descriptions-item>
        <el-descriptions-item label="Original Cabin & Fare">
          {{ cabinClassLabel(originalTicket.cabin_class) }} · {{ fareTypeLabel(originalTicket.fare_type) }}
        </el-descriptions-item>
        <el-descriptions-item label="Original Paid Price">
          <span class="mono-num price">{{ formatCurrency(originalTicket.actual_price) }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <section class="page-section">
      <h2>Change Criteria</h2>
      <div class="change-criteria">
        <div class="criteria-field">
          <label>Route (locked)</label>
          <div class="route-lock">
            <span class="city">{{ searchForm.dep_city || '--' }}</span>
            <el-icon class="route-arrow"><Right /></el-icon>
            <span class="city">{{ searchForm.arr_city || '--' }}</span>
          </div>
        </div>
        <div class="criteria-field">
          <label>Target Date</label>
          <el-date-picker
            v-model="searchForm.flight_date"
            type="date"
            value-format="YYYY-MM-DD"
            :prefix-icon="Calendar"
            placeholder="Select target date"
            class="date-control"
          />
        </div>
        <el-button type="primary" :icon="Search" :loading="searchLoading" @click="openSearchDialog">
          Search Changeable Flights
        </el-button>
      </div>
      <p v-if="!selectedInstance" class="criteria-hint">Click Search Changeable Flights, choose a new flight, then select a cabin fare to calculate fees.</p>
    </section>

    <section v-if="selectedInstance" v-loading="detailLoading || quoteLoading" class="page-section">
      <div class="section-head">
        <h2>New Flight & Cabin</h2>
        <el-button text type="primary" :icon="Search" @click="openSearchDialog">Choose Another Flight</el-button>
      </div>
      <el-descriptions :column="3" border class="instance-summary">
        <el-descriptions-item label="New Instance">{{ selectedInstance.instance_id }}</el-descriptions-item>
        <el-descriptions-item label="Flight No.">{{ selectedInstance.flight_no }}</el-descriptions-item>
        <el-descriptions-item label="Status">{{ instanceStatusLabel(selectedInstance.status) }}</el-descriptions-item>
        <el-descriptions-item label="Route">
          {{ selectedInstance.dep_airport_code }} → {{ selectedInstance.arr_airport_code }}
        </el-descriptions-item>
        <el-descriptions-item label="Date">{{ formatDate(selectedInstance.flight_date) }}</el-descriptions-item>
        <el-descriptions-item label="Time">
          {{ formatTime(selectedInstance.scheduled_departure) }} - {{ formatTime(selectedInstance.scheduled_arrival) }}
        </el-descriptions-item>
      </el-descriptions>

      <el-table :data="cabinPriceChoices" border row-key="key" class="price-table">
        <el-table-column label="Cabin" min-width="120" prop="cabin_class">
          <template #default="{ row }">{{ cabinClassLabel(row.cabin_class) }}</template>
        </el-table-column>
        <el-table-column label="Fare Type" min-width="120" prop="fare_type">
          <template #default="{ row }">{{ fareTypeLabel(row.fare_type) }}</template>
        </el-table-column>
        <el-table-column label="Seats Left" min-width="100" prop="available_seats" />
        <el-table-column label="Price Details" min-width="230">
          <template #default="{ row }">
            <span class="mono-num">
              Ticket {{ formatCurrency(row.price) }} + Fuel & airport fee {{ formatCurrency(selectedInstance?.fuel_infra_fee) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="New Paid Price" width="130">
          <template #default="{ row }">
            <span class="mono-num price">{{ formatCurrency(row.actual_price) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :disabled="selectedPriceKey === row.key" @click="selectCabinPrice(row)">
              {{ selectedPriceKey === row.key ? 'Selected' : 'Select & Quote' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-alert v-if="selectedInstance && !cabinPriceChoices.length" type="warning" show-icon :closable="false" title="No available cabin fares for this instance." />
    </section>

    <section v-if="quote && quoteMatches" class="page-section">
      <h2>Change Fee Details</h2>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="Fee Tier">{{ refundTierLabel(quote.tier) }}</el-descriptions-item>
        <el-descriptions-item label="Fee Rate">{{ feeRateText(quote.fee_rate) }}</el-descriptions-item>
        <el-descriptions-item label="Old Paid Price">
          <span class="mono-num">{{ formatCurrency(quote.old_actual_price) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="New Paid Price">
          <span class="mono-num">{{ formatCurrency(quote.new_actual_price) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="Fare Difference">
          <span class="mono-num" :class="{ danger: (quote.price_diff ?? 0) > 0, success: (quote.price_diff ?? 0) < 0 }">
            {{ formatSignedCurrency(quote.price_diff) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="Fee">
          <span class="mono-num danger">{{ formatCurrency(quote.fee) }}</span>
        </el-descriptions-item>
        <el-descriptions-item :label="settlementLabel">
          <span class="mono-num" :class="{ danger: (quote.amount_user_pays ?? 0) >= 0, success: (quote.amount_user_pays ?? 0) < 0 }">
            {{ formatCurrency(Math.abs(quote.amount_user_pays ?? 0)) }}
          </span>
        </el-descriptions-item>
      </el-descriptions>

      <div class="formula-box mono-num">
        <div>Difference = new paid price {{ formatCurrency(quote.new_actual_price) }} - old paid price {{ formatCurrency(quote.old_actual_price) }} = {{ formatSignedCurrency(quote.price_diff) }}</div>
        <div>Fee = old paid price {{ formatCurrency(quote.old_actual_price) }} × fee rate {{ feeRateText(quote.fee_rate) }} = {{ formatCurrency(quote.fee) }}</div>
        <div>Final amount = fee {{ formatCurrency(quote.fee) }} + difference {{ formatSignedCurrency(quote.price_diff) }} = {{ formatSignedCurrency(quote.amount_user_pays) }}</div>
      </div>

      <div class="actions">
        <el-button type="primary" :icon="Check" :loading="submitLoading" :disabled="!canSubmit" @click="submit">Confirm Change</el-button>
      </div>
    </section>

    <section v-if="result" class="page-section">
      <h2>Change Result</h2>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="Change Record ID">{{ result.refund_id }}</el-descriptions-item>
        <el-descriptions-item label="New Ticket No.">{{ result.new_ticket_no }}</el-descriptions-item>
        <el-descriptions-item label="Old Ticket Status">
          <el-tag type="warning">{{ ticketStatusLabel(result.old_ticket_status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="New Ticket Status">
          <el-tag type="success">{{ ticketStatusLabel(result.new_ticket_status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Fee">
          <span class="mono-num danger">{{ formatCurrency(result.fee) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="Difference">
          <span class="mono-num">{{ formatSignedCurrency(result.price_diff) }}</span>
        </el-descriptions-item>
        <el-descriptions-item :label="result.amount_user_pays >= 0 ? 'Amount Due' : 'Refundable'">
          <span class="mono-num" :class="{ danger: result.amount_user_pays >= 0, success: result.amount_user_pays < 0 }">
            {{ formatCurrency(Math.abs(result.amount_user_pays)) }}
          </span>
        </el-descriptions-item>
      </el-descriptions>
      <div class="actions">
        <el-button :icon="Back" @click="backToOrder">Back to Order Details</el-button>
      </div>
    </section>

    <el-dialog v-model="dialogVisible" title="Select New Flight" width="760px" top="8vh" class="change-dialog">
      <div class="dialog-toolbar">
        <div class="dialog-route">
          <span class="city">{{ searchForm.dep_city }}</span>
          <el-icon class="route-arrow"><Right /></el-icon>
          <span class="city">{{ searchForm.arr_city }}</span>
        </div>
        <el-date-picker
          v-model="searchForm.flight_date"
          type="date"
          value-format="YYYY-MM-DD"
          :prefix-icon="Calendar"
          placeholder="Target date"
          class="dialog-date"
          @change="runSearch"
        />
        <el-button :icon="Search" :loading="searchLoading" @click="runSearch">Search</el-button>
      </div>

      <div v-loading="searchLoading" class="dialog-body">
        <div v-if="candidates.length" class="pick-list">
          <button
            v-for="c in candidates"
            :key="`${c.type}-${c.instance_id}`"
            type="button"
            class="pick-card"
            @click="onPickCandidate(c)"
          >
            <div class="pick-airline">
              <AirlineLogo :code="c.airline_code" :name="c.airline_name" :size="34" />
              <div class="pick-airline-meta">
                <strong>{{ c.airline_name }}</strong>
                <span class="subtle mono-num">{{ c.flight_no }} · {{ c.aircraft_model }}</span>
              </div>
            </div>
            <div class="pick-mid">
              <div class="pick-times">
                <strong class="mono-num">{{ formatTime(c.scheduled_departure) }}</strong>
                <FlightPath :duration="minutesBetween(c.scheduled_departure, c.scheduled_arrival)" :stops="0" compact />
                <strong class="mono-num">{{ formatTime(c.scheduled_arrival) }}</strong>
              </div>
              <div class="pick-sub subtle">
                <span>{{ c.dep_airport_code }} → {{ c.arr_airport_code }}</span>
                <el-tag v-if="c.type === 'nearby'" size="small" type="warning" effect="plain">Nearby Airport</el-tag>
                <span class="seat mono-num">Economy {{ c.economy_left }} / First {{ c.first_left }}</span>
              </div>
            </div>
            <div class="pick-right">
              <div class="pick-price mono-num"><span class="cny">¥</span>{{ c.min_price.toFixed(0) }}<small>from</small></div>
              <span class="pick-select">Select -></span>
            </div>
          </button>
        </div>
        <EmptyState v-else-if="!searchLoading" title="No Changeable Flights" description="Try another travel date." />
      </div>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.change-page {
  display: grid;
  gap: 16px;
  padding: 20px 0 8px;
}

.page-heading {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.page-heading span,
.subtle,
.formula-box {
  color: var(--fa-text-secondary);
  font-size: 13px;
}

.original-ticket,
.instance-summary,
.price-table {
  margin-top: 12px;
}

h2 {
  margin: 0 0 12px;
  font-size: 16px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-head h2 {
  margin: 0;
}

/* ---------- 改签条件 ---------- */
.change-criteria {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-end;
}

.criteria-field {
  display: grid;
  gap: 7px;
}

.criteria-field label {
  color: var(--fa-brand-dark);
  font-size: 13px;
  font-weight: 600;
}

.route-lock {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  height: 40px;
  padding: 0 18px;
  background: var(--fa-surface-2);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
  font-size: 16px;
  font-weight: 700;
  color: var(--fa-text);
}

.route-arrow {
  color: var(--fa-brand);
}

.date-control {
  width: 200px;
}

.criteria-hint {
  margin: 12px 0 0;
  color: var(--fa-text-tertiary);
  font-size: 13px;
}

.price {
  color: var(--fa-danger);
  font-weight: 700;
}

.danger {
  color: var(--fa-danger);
  font-weight: 700;
}

.success {
  color: #1f8f4d;
  font-weight: 700;
}

.formula-box {
  display: grid;
  gap: 6px;
  margin-top: 12px;
  padding: 12px;
  background: var(--fa-bg);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
}

.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

/* ---------- 悬浮小窗：选择改签航班 ---------- */
.dialog-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--fa-border);
}

.dialog-route {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 17px;
  font-weight: 700;
}

.dialog-date {
  width: 180px;
}

.dialog-body {
  min-height: 180px;
}

.pick-list {
  display: grid;
  gap: 10px;
  max-height: 58vh;
  overflow: auto;
  padding-right: 4px;
}

.pick-card {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr) auto;
  gap: 16px;
  align-items: center;
  width: 100%;
  padding: 14px 16px;
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
  background: var(--fa-surface);
  cursor: pointer;
  text-align: left;
  transition: border-color var(--fa-dur-fast) var(--fa-ease), box-shadow var(--fa-dur-base) var(--fa-ease),
    transform var(--fa-dur-base) var(--fa-ease);
}

.pick-card:hover {
  border-color: var(--fa-brand);
  box-shadow: var(--fa-shadow-2);
  transform: translateY(-2px);
}

.pick-airline {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.pick-airline-meta {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.pick-airline-meta strong {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pick-mid {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.pick-times {
  display: grid;
  grid-template-columns: auto minmax(80px, 1fr) auto;
  align-items: center;
  gap: 12px;
}

.pick-times strong {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.pick-sub {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.pick-sub .seat {
  color: var(--fa-text-secondary);
}

.pick-right {
  display: grid;
  justify-items: end;
  gap: 6px;
}

.pick-price {
  color: var(--fa-promo);
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
}

.pick-price .cny {
  font-size: 14px;
  margin-right: 1px;
}

.pick-price small {
  margin-left: 2px;
  color: var(--fa-text-tertiary);
  font-size: 12px;
  font-weight: 600;
}

.pick-select {
  color: var(--fa-brand);
  font-size: 13px;
  font-weight: 600;
}

@media (max-width: 900px) {
  .change-criteria {
    flex-direction: column;
    align-items: stretch;
  }

  .date-control {
    width: 100%;
  }
}

@media (max-width: 700px) {
  .pick-card {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .pick-right {
    justify-items: start;
  }
}
</style>
