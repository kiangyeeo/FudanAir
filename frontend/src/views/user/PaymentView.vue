<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { bookingApi } from '@/api/booking'
import { orderApi } from '@/api/order'
import PaymentCountdown from '@/components/order/PaymentCountdown.vue'
import { useBookingStore } from '@/stores/booking'
import { useAirportStore } from '@/stores/airport'
import { formatChineseDate, formatCurrency, formatDate } from '@/utils/format'
import { cabinClassLabel, fareTypeLabel, orderStatusLabel } from '@/utils/labels'
import type { OrderDetail, OrderTicket } from '@/types/order'

const route = useRoute()
const router = useRouter()
const bookingStore = useBookingStore()
const airportStore = useAirportStore()
const detail = ref<OrderDetail | null>(null)
const detailLoading = ref(false)
const loading = ref(false)
const cancelLoading = ref(false)
const now = ref(Date.now())
let timer: number | undefined

const payMethods = [
  { value: 'wechat', label: 'WeChat Pay', desc: 'Popular mobile wallet', tag: 'W', color: '#07c160' },
  { value: 'alipay', label: 'Alipay', desc: 'Balance / credit pay', tag: 'A', color: '#1677ff' },
  { value: 'bank', label: 'Bank Card', desc: 'Debit / credit card', tag: 'B', color: '#6b7280' },
]
const payMethod = ref('wechat')

const orderNo = computed(() => String(route.params.orderNo || bookingStore.currentOrder?.order_no || ''))
const order = computed(() => {
  if (bookingStore.currentOrder?.order_no === orderNo.value) {
    return bookingStore.currentOrder
  }
  return null
})
const status = computed(() => order.value?.status ?? detail.value?.status ?? '待支付')
const expiresAt = computed(() => order.value?.expires_at ?? fallbackExpiresAt(detail.value?.created_at))
const totalAmount = computed(() => order.value?.total_amount ?? detail.value?.total_amount ?? null)
const ticketCount = computed(() => order.value?.tickets.length ?? detail.value?.tickets.length ?? null)
const isPending = computed(() => status.value === '待支付')
const quantityLabel = computed(() => (isPending.value ? 'Reserved Seats' : 'Tickets'))
interface PriceRow {
  key: string
  label: string
  flightNo: string
  flightDate: string
  depCode: string | null
  arrCode: string | null
  cabin_class: string
  fare_type: string
  ticketPrice: number | null
  fuelFee: number | null
  actualPrice: number
  count: number
  subtotal: number
}

// 客票数据(含航班号/日期/起降机场)优先; 刚下单还没拿到详情时用下单返回的分段做兜底
const priceRows = computed<PriceRow[]>(() => {
  const tickets = detail.value?.tickets ?? []
  if (tickets.length) {
    return rowsFromTickets(tickets)
  }
  const segments = order.value?.amount_breakdown.segments ?? []
  return segments.map((item, index) => ({
    key: `${index}-${item.instance_id}`,
    label: segments.length > 1 ? `Segment ${index + 1}` : 'Segment',
    flightNo: flightNoFromInstance(item.instance_id),
    flightDate: dateFromInstance(item.instance_id),
    depCode: null,
    arrCode: null,
    cabin_class: item.cabin_class,
    fare_type: item.fare_type,
    ticketPrice: item.ticket_price_per_seat,
    fuelFee: item.fuel_infra_fee_per_seat,
    actualPrice: item.actual_price_per_seat,
    count: item.passenger_count,
    subtotal: item.subtotal,
  }))
})

function rowsFromTickets(tickets: OrderTicket[]): PriceRow[] {
  const grouped = new Map<string, PriceRow>()
  for (const ticket of tickets) {
    const fuelFee = ticket.fuel_infra_fee ?? null
    const ticketPrice = ticket.ticket_price ?? (fuelFee !== null ? ticket.actual_price - fuelFee : null)
    const key = `${ticket.instance_id}-${ticket.cabin_class}-${ticket.fare_type}-${ticket.actual_price}`
    const existing = grouped.get(key)
    if (existing) {
      existing.count += 1
      existing.subtotal += ticket.actual_price
      continue
    }
    grouped.set(key, {
      key,
      label: 'Segment',
      flightNo: ticket.flight_no,
      flightDate: ticket.flight_date,
      depCode: ticket.dep_airport_code,
      arrCode: ticket.arr_airport_code,
      cabin_class: ticket.cabin_class,
      fare_type: ticket.fare_type,
      ticketPrice,
      fuelFee,
      actualPrice: ticket.actual_price,
      count: 1,
      subtotal: ticket.actual_price,
    })
  }
  return Array.from(grouped.values()).map((item, index, rows) => ({
    ...item,
    label: rows.length > 1 ? `Segment ${index + 1}` : item.label,
  }))
}

// 实例号形如 {航班号}_{yyyymmdd}; 兜底时由它还原航班号与日期
function flightNoFromInstance(instanceId: string): string {
  const idx = instanceId.lastIndexOf('_')
  return idx > 0 ? instanceId.slice(0, idx) : instanceId
}

function dateFromInstance(instanceId: string): string {
  const idx = instanceId.lastIndexOf('_')
  const raw = idx > 0 ? instanceId.slice(idx + 1) : ''
  return /^\d{8}$/.test(raw) ? `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}` : raw
}
const isExpired = computed(() => {
  if (!expiresAt.value || !isPending.value) {
    return false
  }
  return new Date(expiresAt.value).getTime() <= now.value
})
const canPay = computed(() => Boolean(orderNo.value) && isPending.value && !isExpired.value)

async function pay() {
  if (!orderNo.value) {
    ElMessage.warning('Missing order number')
    return
  }
  if (!canPay.value) {
    ElMessage.warning(isExpired.value ? 'Order has expired' : 'This order cannot be paid')
    return
  }
  loading.value = true
  try {
    await bookingApi.pay(orderNo.value)
    bookingStore.finish()
    ElMessage.success('Payment successful')
    router.push(`/orders/${orderNo.value}`)
  } finally {
    loading.value = false
  }
}

async function cancelOrder() {
  if (!orderNo.value) {
    ElMessage.warning('Missing order number')
    return
  }
  try {
    await ElMessageBox.confirm('Cancel this pending order? Reserved inventory will be released.', 'Cancel Order', {
      confirmButtonText: 'Cancel Order',
      cancelButtonText: 'Keep Order',
      type: 'warning',
    })
  } catch {
    return
  }

  cancelLoading.value = true
  try {
    await bookingApi.cancel(orderNo.value)
    bookingStore.clearCurrentOrder()
    ElMessage.success('Order canceled')
    router.push('/orders')
  } finally {
    cancelLoading.value = false
  }
}

async function loadDetail() {
  if (!orderNo.value) {
    return
  }
  detailLoading.value = true
  try {
    detail.value = await orderApi.getDetail(orderNo.value)
    bookingStore.setLatestOrderNo(orderNo.value)
  } finally {
    detailLoading.value = false
  }
}

function fallbackExpiresAt(createdAt?: string | null) {
  if (!createdAt) {
    return null
  }
  return new Date(new Date(createdAt).getTime() + 15 * 60 * 1000).toISOString()
}

onMounted(() => {
  timer = window.setInterval(() => {
    now.value = Date.now()
  }, 1000)
  void airportStore.ensureLoaded()
  void loadDetail()
})

onBeforeUnmount(() => {
  if (timer) {
    window.clearInterval(timer)
  }
})

watch(orderNo, () => {
  detail.value = null
  void loadDetail()
})
</script>

<template>
  <div class="page-shell payment-page">
    <section v-loading="detailLoading" class="page-section payment-panel">
      <div class="pay-head">
        <div>
          <h1 class="page-title">Payment</h1>
          <span class="order-no mono-num">Order {{ orderNo || '--' }} · {{ orderStatusLabel(status) }}</span>
        </div>
        <PaymentCountdown v-if="isPending && expiresAt" :expires-at="expiresAt" />
      </div>

      <el-alert v-if="isExpired" type="warning" show-icon :closable="false" title="The 15-minute payment window has expired. Return to the order list to check status." />

      <el-descriptions :column="2" border>
        <el-descriptions-item label="Order No.">{{ orderNo || '--' }}</el-descriptions-item>
        <el-descriptions-item label="Order Status">{{ orderStatusLabel(status) }}</el-descriptions-item>
        <el-descriptions-item :label="quantityLabel">{{ ticketCount ?? '--' }}</el-descriptions-item>
        <el-descriptions-item label="Created At">{{ formatDate(order?.created_at ?? detail?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="Payment Deadline" :span="2">{{ formatDate(expiresAt) }}</el-descriptions-item>
      </el-descriptions>

      <el-table v-if="priceRows.length" :data="priceRows" border row-key="key">
        <el-table-column prop="label" label="Segment" width="90" />
        <el-table-column label="Flight" min-width="220">
          <template #default="{ row }">
            <div class="flight-name mono-num">{{ row.flightNo }}</div>
            <div class="subtle">{{ formatChineseDate(row.flightDate) }}</div>
            <div v-if="row.depCode && row.arrCode" class="subtle">
              {{ airportStore.display(row.depCode) }} → {{ airportStore.display(row.arrCode) }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Cabin & Fare" min-width="240">
          <template #default="{ row }">
            <div>{{ cabinClassLabel(row.cabin_class) }} · {{ fareTypeLabel(row.fare_type) }}</div>
            <span class="subtle mono-num">
              Ticket {{ formatCurrency(row.ticketPrice) }} + Fuel & airport fee {{ formatCurrency(row.fuelFee) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="Qty" width="90">
          <template #default="{ row }">{{ row.count }}</template>
        </el-table-column>
        <el-table-column label="Subtotal" width="130">
          <template #default="{ row }">
            <span class="price mono-num">{{ formatCurrency(row.subtotal) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="isPending && !isExpired" class="pay-methods">
        <h2 class="block-title">Select Payment Method</h2>
        <div class="method-grid">
          <button
            v-for="method in payMethods"
            :key="method.value"
            type="button"
            class="method-card"
            :class="{ active: payMethod === method.value }"
            @click="payMethod = method.value"
          >
            <span class="method-tag" :style="{ background: method.color }">{{ method.tag }}</span>
            <span class="method-info">
              <strong>{{ method.label }}</strong>
              <small>{{ method.desc }}</small>
            </span>
            <span class="method-radio" />
          </button>
        </div>
      </div>

      <div class="pay-bar">
        <div class="pay-total">
          Amount Due <span class="price mono-num">{{ formatCurrency(totalAmount) }}</span>
        </div>
        <div class="actions">
          <el-button :disabled="!isPending" :loading="cancelLoading" @click="cancelOrder">Cancel Order</el-button>
          <el-button type="primary" size="large" :disabled="!canPay" :loading="loading" @click="pay">Pay Now</el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.payment-page {
  padding: 20px 0 8px;
}

.payment-panel {
  display: grid;
  gap: 18px;
}

.pay-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.pay-head .page-title {
  margin-bottom: 4px;
}

.order-no {
  color: var(--fa-text-tertiary);
  font-size: 13px;
}

.block-title {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 700;
}

.method-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.method-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1.5px solid var(--fa-border);
  border-radius: var(--fa-radius);
  background: var(--fa-surface);
  cursor: pointer;
  transition: border-color var(--fa-dur-fast) var(--fa-ease), box-shadow var(--fa-dur-base) var(--fa-ease);
}

.method-card:hover {
  border-color: var(--fa-brand);
}

.method-card.active {
  border-color: var(--fa-brand);
  box-shadow: 0 0 0 3px rgba(22, 119, 255, 0.12);
}

.method-tag {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
}

.method-info {
  display: grid;
  gap: 2px;
  flex: 1;
  text-align: left;
}

.method-info strong {
  font-size: 14px;
}

.method-info small {
  color: var(--fa-text-tertiary);
  font-size: 12px;
}

.method-radio {
  width: 18px;
  height: 18px;
  border: 2px solid var(--fa-border-strong);
  border-radius: 50%;
  transition: all var(--fa-dur-fast) var(--fa-ease);
}

.method-card.active .method-radio {
  border-color: var(--fa-brand);
  border-width: 5px;
}

.pay-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding-top: 16px;
  border-top: 1px solid var(--fa-border);
}

.pay-total {
  color: var(--fa-text-secondary);
  font-size: 14px;
}

.pay-total .price {
  margin-left: 6px;
  font-size: 26px;
}

.price {
  color: var(--fa-promo);
  font-weight: 800;
}

.flight-name {
  font-weight: 600;
}

.subtle {
  color: var(--fa-text-secondary);
  font-size: 12px;
}

.actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

@media (max-width: 600px) {
  .pay-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .actions {
    justify-content: stretch;
  }

  .actions :deep(.el-button) {
    flex: 1;
  }
}
</style>
