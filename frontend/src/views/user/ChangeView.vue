<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Back, Check, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { flightApi } from '@/api/flight'
import { orderApi } from '@/api/order'
import { refundApi } from '@/api/refund'
import { searchApi } from '@/api/search'
import CityAutocomplete from '@/components/flight/CityAutocomplete.vue'
import { formatCurrency, formatDate, formatTime } from '@/utils/format'
import type { CabinClass, FareType } from '@/types/common'
import type { CabinPrice, FlightInstance } from '@/types/flight'
import type { OrderDetail, OrderTicket } from '@/types/order'
import type { ChangeRequest, ChangeTicketResponse, RefundQuote } from '@/types/refund'
import type { DirectFlightCandidate, FlightSearchRequest, NearbyFlightCandidate } from '@/types/search'

type ChangeCandidate = DirectFlightCandidate | NearbyFlightCandidate

interface CabinPriceChoice extends CabinPrice {
  key: string
  actual_price: number
}

const route = useRoute()
const router = useRouter()
const orderNo = ref('')
const originalTicket = ref<OrderTicket | null>(null)
const originalLoading = ref(false)
const searchLoading = ref(false)
const detailLoading = ref(false)
const quoteLoading = ref(false)
const submitLoading = ref(false)
const candidates = ref<ChangeCandidate[]>([])
const selectedCandidate = ref<ChangeCandidate | null>(null)
const selectedInstance = ref<FlightInstance | null>(null)
const selectedPriceKey = ref('')
const quote = ref<RefundQuote | null>(null)
const result = ref<ChangeTicketResponse | null>(null)
const cities = ref<string[]>([])

const form = reactive<ChangeRequest>({
  ticket_no: '',
  new_instance_id: '',
  new_cabin_class: '经济舱',
  new_fare_type: '标准',
})

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
const settlementLabel = computed(() => ((quote.value?.amount_user_pays ?? 0) >= 0 ? '需补缴' : '可退还'))
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
      ElMessage.warning('订单中未找到当前客票')
      return
    }
    await fillSearchCities(originalTicket.value)
  } catch {
    ElMessage.warning('未能自动回填改签搜索条件')
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

async function loadCities() {
  try {
    cities.value = await flightApi.listCities()
  } catch {
    cities.value = []
  }
}

async function runSearch() {
  const payload = searchPayload()
  if (!payload) {
    return
  }

  resetTarget()
  searchLoading.value = true
  try {
    const data = await searchApi.searchFlights(payload)
    candidates.value = [...data.direct, ...data.nearby]
    if (!candidates.value.length) {
      ElMessage.info('暂无可改签的直飞或临近机场航班')
    }
  } finally {
    searchLoading.value = false
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
    const first = cabinPriceChoices.value[0]
    if (!first) {
      ElMessage.warning('该航班暂无可售舱位票价')
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
    ElMessage.warning('请先完成改签费用试算')
    return
  }

  try {
    await ElMessageBox.confirm(confirmText(), '确认改签', {
      confirmButtonText: '确认改签',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  submitLoading.value = true
  try {
    result.value = await refundApi.change({ ...form, ticket_no: normalizedTicketNo.value })
    ElMessage.success('改签申请已提交')
  } finally {
    submitLoading.value = false
  }
}

function searchPayload(): FlightSearchRequest | null {
  const depCity = searchForm.dep_city.trim()
  const arrCity = searchForm.arr_city.trim()
  if (!depCity || !arrCity || !searchForm.flight_date) {
    ElMessage.warning('请填写出发城市、到达城市和目标日期')
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
    ElMessage.warning('请填写原客票号')
    return false
  }
  if (!form.new_instance_id || !form.new_cabin_class || !form.new_fare_type) {
    ElMessage.warning('请选择新航班和舱位票价')
    return false
  }
  return true
}

function resetTarget() {
  candidates.value = []
  selectedCandidate.value = null
  selectedInstance.value = null
  selectedPriceKey.value = ''
  form.new_instance_id = ''
  quote.value = null
  result.value = null
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
  return `确认将 ${normalizedTicketNo.value} 改签到 ${form.new_instance_id}？${settlementLabel.value} ${formatCurrency(Math.abs(amount))}。`
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

function candidateTypeText(candidate: ChangeCandidate) {
  return candidate.type === 'nearby' ? '临近机场' : '直飞'
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
  void loadCities()
  void loadOriginalTicket()
})
</script>

<template>
  <div class="page-shell change-page">
    <section v-loading="originalLoading" class="page-section">
      <div class="page-heading">
        <div>
          <h1 class="page-title">改签</h1>
          <span>选择新航班实例和舱位票价后试算手续费与差价。</span>
        </div>
        <el-button v-if="orderNo" :icon="Back" @click="backToOrder">返回订单</el-button>
      </div>

      <el-descriptions v-if="originalTicket" :column="3" border class="original-ticket">
        <el-descriptions-item label="原客票">{{ originalTicket.ticket_no }}</el-descriptions-item>
        <el-descriptions-item label="乘机人">{{ originalTicket.passenger.real_name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="originalTicket.status === '有效' ? 'success' : 'info'">{{ originalTicket.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="原航班">
          {{ originalTicket.flight_no }} · {{ originalTicket.instance_id }}
        </el-descriptions-item>
        <el-descriptions-item label="航线">
          {{ originalTicket.dep_airport_code }} → {{ originalTicket.arr_airport_code }}
        </el-descriptions-item>
        <el-descriptions-item label="日期时间">
          {{ formatDate(originalTicket.flight_date) }} {{ formatTime(originalTicket.scheduled_departure) }} - {{ formatTime(originalTicket.scheduled_arrival) }}
        </el-descriptions-item>
        <el-descriptions-item label="原舱位票价">
          {{ originalTicket.cabin_class }} · {{ originalTicket.fare_type }}
        </el-descriptions-item>
        <el-descriptions-item label="原成交价">
          <span class="mono-num price">{{ formatCurrency(originalTicket.actual_price) }}</span>
        </el-descriptions-item>
      </el-descriptions>

      <el-form :model="form" label-position="top" class="ticket-form">
        <el-form-item label="原客票号">
          <el-input v-model="form.ticket_no" placeholder="输入原客票号" clearable />
        </el-form-item>
      </el-form>
    </section>

    <section class="page-section">
      <h2>搜索新航班</h2>
      <el-form :model="searchForm" label-position="top" class="search-form">
        <el-form-item label="出发城市">
          <CityAutocomplete v-model="searchForm.dep_city" :cities="cities" placeholder="输入出发城市" />
        </el-form-item>
        <el-form-item label="到达城市">
          <CityAutocomplete v-model="searchForm.arr_city" :cities="cities" placeholder="输入到达城市" />
        </el-form-item>
        <el-form-item label="目标日期">
          <el-date-picker v-model="searchForm.flight_date" type="date" value-format="YYYY-MM-DD" placeholder="选择目标日期" />
        </el-form-item>
        <el-form-item label=" ">
          <el-button type="primary" :icon="Search" :loading="searchLoading" @click="runSearch">搜索</el-button>
        </el-form-item>
      </el-form>

      <el-table
        v-if="candidates.length"
        v-loading="searchLoading"
        :data="candidates"
        border
        row-key="instance_id"
        highlight-current-row
        class="candidate-table"
      >
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.type === 'nearby' ? 'warning' : 'success'">{{ candidateTypeText(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="航班" min-width="180">
          <template #default="{ row }">
            <div>{{ row.airline_name }} {{ row.flight_no }}</div>
            <span class="subtle">{{ row.instance_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="航线" min-width="150">
          <template #default="{ row }">{{ row.dep_airport_code }} → {{ row.arr_airport_code }}</template>
        </el-table-column>
        <el-table-column label="时间" min-width="150">
          <template #default="{ row }">{{ formatTime(row.scheduled_departure) }} - {{ formatTime(row.scheduled_arrival) }}</template>
        </el-table-column>
        <el-table-column label="余票" min-width="140">
          <template #default="{ row }">经济舱 {{ row.economy_left }} / 头等舱 {{ row.first_left }}</template>
        </el-table-column>
        <el-table-column label="起价" width="130">
          <template #default="{ row }">
            <span class="mono-num price">{{ formatCurrency(row.min_price) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              :loading="detailLoading && selectedCandidate?.instance_id === row.instance_id"
              @click="selectCandidate(row)"
            >
              选择
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section v-if="selectedInstance" v-loading="detailLoading || quoteLoading" class="page-section">
      <h2>选择舱位票价</h2>
      <el-descriptions :column="3" border class="instance-summary">
        <el-descriptions-item label="新实例">{{ selectedInstance.instance_id }}</el-descriptions-item>
        <el-descriptions-item label="航班号">{{ selectedInstance.flight_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ selectedInstance.status }}</el-descriptions-item>
        <el-descriptions-item label="航线">
          {{ selectedInstance.dep_airport_code }} → {{ selectedInstance.arr_airport_code }}
        </el-descriptions-item>
        <el-descriptions-item label="日期">{{ formatDate(selectedInstance.flight_date) }}</el-descriptions-item>
        <el-descriptions-item label="时间">
          {{ formatTime(selectedInstance.scheduled_departure) }} - {{ formatTime(selectedInstance.scheduled_arrival) }}
        </el-descriptions-item>
      </el-descriptions>

      <el-table :data="cabinPriceChoices" border row-key="key" class="price-table">
        <el-table-column label="舱位" min-width="120" prop="cabin_class" />
        <el-table-column label="票价类型" min-width="120" prop="fare_type" />
        <el-table-column label="余票" min-width="100" prop="available_seats" />
        <el-table-column label="价格明细" min-width="230">
          <template #default="{ row }">
            <span class="mono-num">
              机票 {{ formatCurrency(row.price) }} + 燃油基建 {{ formatCurrency(selectedInstance?.fuel_infra_fee) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="新成交价" width="130">
          <template #default="{ row }">
            <span class="mono-num price">{{ formatCurrency(row.actual_price) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :disabled="selectedPriceKey === row.key" @click="selectCabinPrice(row)">
              {{ selectedPriceKey === row.key ? '已选择' : '选择试算' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-alert v-if="selectedInstance && !cabinPriceChoices.length" type="warning" show-icon :closable="false" title="该实例暂无可售舱位票价。" />
    </section>

    <section v-if="quote && quoteMatches" class="page-section">
      <h2>改签费用明细</h2>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="费率档位">{{ quote.tier }}</el-descriptions-item>
        <el-descriptions-item label="手续费率">{{ feeRateText(quote.fee_rate) }}</el-descriptions-item>
        <el-descriptions-item label="旧票成交价">
          <span class="mono-num">{{ formatCurrency(quote.old_actual_price) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="新票成交价">
          <span class="mono-num">{{ formatCurrency(quote.new_actual_price) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="票价差额">
          <span class="mono-num" :class="{ danger: (quote.price_diff ?? 0) > 0, success: (quote.price_diff ?? 0) < 0 }">
            {{ formatSignedCurrency(quote.price_diff) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="手续费">
          <span class="mono-num danger">{{ formatCurrency(quote.fee) }}</span>
        </el-descriptions-item>
        <el-descriptions-item :label="settlementLabel">
          <span class="mono-num" :class="{ danger: (quote.amount_user_pays ?? 0) >= 0, success: (quote.amount_user_pays ?? 0) < 0 }">
            {{ formatCurrency(Math.abs(quote.amount_user_pays ?? 0)) }}
          </span>
        </el-descriptions-item>
      </el-descriptions>

      <div class="formula-box mono-num">
        <div>差价 = 新票成交价 {{ formatCurrency(quote.new_actual_price) }} - 旧票成交价 {{ formatCurrency(quote.old_actual_price) }} = {{ formatSignedCurrency(quote.price_diff) }}</div>
        <div>手续费 = 旧票成交价 {{ formatCurrency(quote.old_actual_price) }} × 手续费率 {{ feeRateText(quote.fee_rate) }} = {{ formatCurrency(quote.fee) }}</div>
        <div>最终金额 = 手续费 {{ formatCurrency(quote.fee) }} + 差价 {{ formatSignedCurrency(quote.price_diff) }} = {{ formatSignedCurrency(quote.amount_user_pays) }}</div>
      </div>

      <div class="actions">
        <el-button type="primary" :icon="Check" :loading="submitLoading" :disabled="!canSubmit" @click="submit">确认改签</el-button>
      </div>
    </section>

    <section v-if="result" class="page-section">
      <h2>改签结果</h2>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="退改记录 ID">{{ result.refund_id }}</el-descriptions-item>
        <el-descriptions-item label="新票号">{{ result.new_ticket_no }}</el-descriptions-item>
        <el-descriptions-item label="旧票状态">
          <el-tag type="warning">{{ result.old_ticket_status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="新票状态">
          <el-tag type="success">{{ result.new_ticket_status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="手续费">
          <span class="mono-num danger">{{ formatCurrency(result.fee) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="差价">
          <span class="mono-num">{{ formatSignedCurrency(result.price_diff) }}</span>
        </el-descriptions-item>
        <el-descriptions-item :label="result.amount_user_pays >= 0 ? '需补缴' : '可退还'">
          <span class="mono-num" :class="{ danger: result.amount_user_pays >= 0, success: result.amount_user_pays < 0 }">
            {{ formatCurrency(Math.abs(result.amount_user_pays)) }}
          </span>
        </el-descriptions-item>
      </el-descriptions>
      <div class="actions">
        <el-button :icon="Back" @click="backToOrder">返回订单详情</el-button>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.change-page {
  display: grid;
  gap: 16px;
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
.ticket-form,
.candidate-table,
.instance-summary,
.price-table {
  margin-top: 12px;
}

.ticket-form {
  max-width: 360px;
}

.search-form {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) minmax(180px, 1fr) 180px auto;
  gap: 12px;
  align-items: end;
}

h2 {
  margin: 0 0 12px;
  font-size: 16px;
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

@media (max-width: 900px) {
  .search-form {
    grid-template-columns: 1fr;
  }
}
</style>
