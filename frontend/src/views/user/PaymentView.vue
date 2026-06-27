<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { bookingApi } from '@/api/booking'
import { orderApi } from '@/api/order'
import PaymentCountdown from '@/components/order/PaymentCountdown.vue'
import { useBookingStore } from '@/stores/booking'
import { formatCurrency, formatDate } from '@/utils/format'
import type { OrderDetail } from '@/types/order'

const route = useRoute()
const router = useRouter()
const bookingStore = useBookingStore()
const detail = ref<OrderDetail | null>(null)
const detailLoading = ref(false)
const loading = ref(false)
const cancelLoading = ref(false)
const now = ref(Date.now())
let timer: number | undefined

const payMethods = [
  { value: 'wechat', label: '微信支付', desc: '亿万用户的选择', tag: '微', color: '#07c160' },
  { value: 'alipay', label: '支付宝', desc: '账户余额 / 花呗', tag: '支', color: '#1677ff' },
  { value: 'bank', label: '银行卡', desc: '储蓄卡 / 信用卡', tag: '卡', color: '#6b7280' },
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
const priceRows = computed(() => {
  const segments = order.value?.amount_breakdown.segments ?? []
  if (segments.length) {
    return segments.map((item, index) => ({
      key: `${index}-${item.instance_id}`,
      label: segments.length > 1 ? `第 ${index + 1} 段` : '航段',
      instance_id: item.instance_id,
      cabin_class: item.cabin_class,
      fare_type: item.fare_type,
      ticketPrice: item.ticket_price_per_seat,
      fuelFee: item.fuel_infra_fee_per_seat,
      actualPrice: item.actual_price_per_seat,
      count: item.passenger_count,
      subtotal: item.subtotal,
    }))
  }

  const grouped = new Map<string, {
    key: string
    label: string
    instance_id: string
    cabin_class: string
    fare_type: string
    ticketPrice: number | null
    fuelFee: number | null
    actualPrice: number
    count: number
    subtotal: number
  }>()
  for (const ticket of detail.value?.tickets ?? []) {
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
      instance_id: ticket.instance_id,
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
})
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
  if (!orderNo.value || order.value) {
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
        <el-table-column prop="instance_id" label="航班实例" min-width="180" />
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
