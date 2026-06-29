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
  { value: 'wechat', label: '微信支付', desc: '亿万用户的选择', icon: 'wechat' },
  { value: 'alipay', label: '支付宝', desc: '账户余额 / 花呗', icon: 'alipay' },
  { value: 'bank', label: '银行卡', desc: '储蓄卡 / 信用卡', icon: 'bank' },
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
const quantityLabel = computed(() => (isPending.value ? '锁座数量' : '客票数量'))
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
    label: segments.length > 1 ? `第 ${index + 1} 段` : '航段',
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
      label: '航段',
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
    label: rows.length > 1 ? `第 ${index + 1} 段` : item.label,
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
    ElMessage.warning('缺少订单号')
    return
  }
  if (!canPay.value) {
    ElMessage.warning(isExpired.value ? '订单已超时' : '当前订单不可支付')
    return
  }
  loading.value = true
  try {
    await bookingApi.pay(orderNo.value)
    bookingStore.finish()
    ElMessage.success('支付成功')
    router.push(`/orders/${orderNo.value}`)
  } finally {
    loading.value = false
  }
}

async function cancelOrder() {
  if (!orderNo.value) {
    ElMessage.warning('缺少订单号')
    return
  }
  try {
    await ElMessageBox.confirm('确认取消该待支付订单？库存会释放。', '取消订单', {
      confirmButtonText: '确认取消',
      cancelButtonText: '再看看',
      type: 'warning',
    })
  } catch {
    return
  }

  cancelLoading.value = true
  try {
    await bookingApi.cancel(orderNo.value)
    bookingStore.clearCurrentOrder()
    ElMessage.success('订单已取消')
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
          <h1 class="page-title">订单支付</h1>
          <span class="order-no mono-num">订单号 {{ orderNo || '--' }} · {{ status }}</span>
        </div>
        <PaymentCountdown v-if="isPending && expiresAt" :expires-at="expiresAt" />
      </div>

      <el-alert v-if="isExpired" type="warning" show-icon :closable="false" title="订单已超过 15 分钟支付窗口，请返回订单列表查看状态。" />

      <el-descriptions :column="2" border>
        <el-descriptions-item label="订单号">{{ orderNo || '--' }}</el-descriptions-item>
        <el-descriptions-item label="订单状态">{{ status }}</el-descriptions-item>
        <el-descriptions-item :label="quantityLabel">{{ ticketCount ?? '--' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(order?.created_at ?? detail?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="支付截止" :span="2">{{ formatDate(expiresAt) }}</el-descriptions-item>
      </el-descriptions>

      <el-table v-if="priceRows.length" :data="priceRows" border row-key="key">
        <el-table-column prop="label" label="航段" width="90" />
        <el-table-column label="航班" min-width="220">
          <template #default="{ row }">
            <div class="flight-name mono-num">{{ row.flightNo }}</div>
            <div class="subtle">{{ formatChineseDate(row.flightDate) }}</div>
            <div v-if="row.depCode && row.arrCode" class="subtle">
              {{ airportStore.display(row.depCode) }} → {{ airportStore.display(row.arrCode) }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="舱位票价" min-width="240">
          <template #default="{ row }">
            <div>{{ row.cabin_class }} · {{ row.fare_type }}</div>
            <span class="subtle mono-num">
              机票 {{ formatCurrency(row.ticketPrice) }} + 燃油基建 {{ formatCurrency(row.fuelFee) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="90">
          <template #default="{ row }">{{ row.count }}</template>
        </el-table-column>
        <el-table-column label="小计" width="130">
          <template #default="{ row }">
            <span class="price mono-num">{{ formatCurrency(row.subtotal) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="isPending && !isExpired" class="pay-methods">
        <h2 class="block-title">选择支付方式</h2>
        <div class="method-grid">
          <button
            v-for="method in payMethods"
            :key="method.value"
            type="button"
            class="method-card"
            :class="{ active: payMethod === method.value }"
            @click="payMethod = method.value"
          >
            <span class="method-logo" :class="`method-logo-${method.value}`" aria-hidden="true">
              <svg v-if="method.icon === 'wechat'" viewBox="0 0 48 48" role="img">
                <path fill="#07c160" d="M4 24c0-11.05 8.95-20 20-20s20 8.95 20 20-8.95 20-20 20S4 35.05 4 24Z" />
                <path fill="#fff" d="M21.1 16.1c-5.8 0-10.5 3.8-10.5 8.4 0 2.6 1.5 4.9 3.9 6.4l-.8 2.7 3.1-1.6c1.3.5 2.8.8 4.3.8.5 0 1 0 1.5-.1-.3-.8-.5-1.6-.5-2.5 0-4.2 4-7.6 9.2-7.8-1.2-3.6-5.2-6.3-10.2-6.3Zm-3.6 6.3a1.2 1.2 0 1 1 0-2.4 1.2 1.2 0 0 1 0 2.4Zm7.2 0a1.2 1.2 0 1 1 0-2.4 1.2 1.2 0 0 1 0 2.4Z" />
                <path fill="#fff" d="M32.1 24.4c-4.5 0-8.1 2.9-8.1 6.4s3.6 6.4 8.1 6.4c1.1 0 2.2-.2 3.1-.5l2.4 1.2-.6-2.1c1.9-1.1 3.1-2.9 3.1-5 0-3.5-3.6-6.4-8-6.4Zm-2.8 4.8a1 1 0 1 1 0-2 1 1 0 0 1 0 2Zm5.7 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z" />
              </svg>
              <svg v-else-if="method.icon === 'alipay'" viewBox="0 0 48 48" role="img">
                <path fill="#1677ff" d="M4 10a6 6 0 0 1 6-6h28a6 6 0 0 1 6 6v28a6 6 0 0 1-6 6H10a6 6 0 0 1-6-6V10Z" />
                <path fill="#fff" d="M35.3 31.2c-2.5-1.5-5.5-2.7-8.9-3.5 1.3-2.2 2.1-4.7 2.5-7.4h7v-3.5H26V12h-4v4.8H12v3.5h12.9c-.4 2.4-1.2 4.6-2.5 6.4-5.6-.8-10-.1-10.9 2.8-.7 2.4 1.3 4.8 4.9 5.9 3.5 1 6.7-.2 9.2-2.9 2.9.8 5.5 2 7.7 3.4l2-4.7Zm-15.4-.1c-1.2 1-2.4 1.3-3.7.9-1.2-.4-1.9-1-1.7-1.6.3-1 2.7-1.1 6-.7-.2.5-.4.9-.6 1.4Z" />
              </svg>
              <svg v-else viewBox="0 0 48 48" role="img">
                <path fill="#4b5563" d="M7 14a5 5 0 0 1 5-5h24a5 5 0 0 1 5 5v20a5 5 0 0 1-5 5H12a5 5 0 0 1-5-5V14Z" />
                <path fill="#fff" d="M11 17h26v5H11v-5Zm4 11h11v3H15v-3Zm0 5h17v3H15v-3Z" opacity=".95" />
              </svg>
            </span>
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
          应付金额 <span class="price mono-num">{{ formatCurrency(totalAmount) }}</span>
        </div>
        <div class="actions">
          <el-button :disabled="!isPending" :loading="cancelLoading" @click="cancelOrder">取消订单</el-button>
          <el-button type="primary" size="large" :disabled="!canPay" :loading="loading" @click="pay">确认支付</el-button>
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

.method-logo {
  display: grid;
  place-items: center;
  flex: 0 0 40px;
  width: 40px;
  height: 40px;
}

.method-logo svg {
  display: block;
  width: 40px;
  height: 40px;
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
