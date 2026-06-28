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

function openSearchDialog() {
  if (!searchForm.dep_city || !searchForm.arr_city) {
    ElMessage.warning('未获取到原航线城市，无法搜索')
    return
  }
  if (!searchForm.flight_date) {
    ElMessage.warning('请选择目标日期')
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
    ElMessage.warning('请选择目标日期')
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
    ElMessage.warning('缺少原客票号')
    return false
  }
  if (!form.new_instance_id || !form.new_cabin_class || !form.new_fare_type) {
    ElMessage.warning('请选择新航班和舱位票价')
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
    ElMessage.warning(`该航班实例当前为${instance.status},不可改签`)
    return false
  }
  if (isDeparted(instance)) {
    ElMessage.warning('该航班已起飞,不可改签')
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
          <h1 class="page-title">改签</h1>
          <span>出发与到达城市保持不变，可更改出行日期并重新选择航班。</span>
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
    </section>

    <section class="page-section">
      <h2>改签条件</h2>
      <div class="change-criteria">
        <div class="criteria-field">
          <label>航线（不可更改）</label>
          <div class="route-lock">
            <span class="city">{{ searchForm.dep_city || '--' }}</span>
            <el-icon class="route-arrow"><Right /></el-icon>
            <span class="city">{{ searchForm.arr_city || '--' }}</span>
          </div>
        </div>
        <div class="criteria-field">
          <label>目标日期</label>
          <el-date-picker
            v-model="searchForm.flight_date"
            type="date"
            value-format="YYYY-MM-DD"
            :prefix-icon="Calendar"
            placeholder="选择目标日期"
            class="date-control"
          />
        </div>
        <el-button type="primary" :icon="Search" :loading="searchLoading" @click="openSearchDialog">
          搜索可改签航班
        </el-button>
      </div>
      <p v-if="!selectedInstance" class="criteria-hint">点击「搜索可改签航班」，在弹窗中挑选新的航班后再选舱位试算费用。</p>
    </section>

    <section v-if="selectedInstance" v-loading="detailLoading || quoteLoading" class="page-section">
      <div class="section-head">
        <h2>新航班与舱位</h2>
        <el-button text type="primary" :icon="Search" @click="openSearchDialog">重新选择航班</el-button>
      </div>
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

    <el-dialog v-model="dialogVisible" title="选择改签航班" width="760px" top="8vh" class="change-dialog">
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
          placeholder="目标日期"
          class="dialog-date"
          @change="runSearch"
        />
        <el-button :icon="Search" :loading="searchLoading" @click="runSearch">搜索</el-button>
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
                <el-tag v-if="c.type === 'nearby'" size="small" type="warning" effect="plain">临近机场</el-tag>
                <span class="seat mono-num">经济 {{ c.economy_left }} / 头等 {{ c.first_left }}</span>
              </div>
            </div>
            <div class="pick-right">
              <div class="pick-price mono-num"><span class="cny">¥</span>{{ c.min_price.toFixed(0) }}<small>起</small></div>
              <span class="pick-select">选择 →</span>
            </div>
          </button>
        </div>
        <EmptyState v-else-if="!searchLoading" title="暂无可改签航班" description="换个出行日期再试试。" />
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
