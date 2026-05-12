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

.actions {
  display: flex;
  justify-content: flex-end;
}
</style>
