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
  <div class="page-shell">
    <section v-loading="detailLoading" class="page-section payment-panel">
      <div>
        <h1 class="page-title">模拟支付</h1>
        <PaymentCountdown v-if="isPending && expiresAt" :expires-at="expiresAt" />
        <el-alert v-if="isExpired" type="warning" show-icon :closable="false" title="订单已超过 15 分钟支付窗口，请返回订单列表查看状态。" />
      </div>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="订单号">{{ orderNo || '--' }}</el-descriptions-item>
        <el-descriptions-item label="订单状态">{{ status }}</el-descriptions-item>
        <el-descriptions-item label="应付金额">
          <span class="price mono-num">{{ formatCurrency(totalAmount) }}</span>
        </el-descriptions-item>
        <el-descriptions-item :label="quantityLabel">{{ ticketCount ?? '--' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(order?.created_at ?? detail?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="支付截止">{{ formatDate(expiresAt) }}</el-descriptions-item>
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
      <div class="actions">
        <el-button :disabled="!isPending" :loading="cancelLoading" @click="cancelOrder">取消订单</el-button>
        <el-button type="primary" :disabled="!canPay" :loading="loading" @click="pay">确认支付</el-button>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.payment-panel {
  display: grid;
  gap: 16px;
}

.price {
  color: var(--fa-danger);
  font-weight: 700;
}

.subtle {
  color: var(--fa-text-secondary);
  font-size: 12px;
}

.actions {
  display: flex;
  justify-content: flex-end;
}
</style>
