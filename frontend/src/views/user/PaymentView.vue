<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { bookingApi } from '@/api/booking'
import PaymentCountdown from '@/components/order/PaymentCountdown.vue'
import { useBookingStore } from '@/stores/booking'
import { formatCurrency } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const bookingStore = useBookingStore()
const loading = ref(false)

const orderNo = computed(() => String(route.params.orderNo || bookingStore.currentOrder?.order_no || ''))
const order = computed(() => bookingStore.currentOrder)

async function pay() {
  if (!orderNo.value) {
    ElMessage.warning('缺少订单号')
    return
  }
  loading.value = true
  try {
    await bookingApi.pay(orderNo.value)
    ElMessage.success('支付成功')
    router.push(`/orders/${orderNo.value}`)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-shell">
    <section class="page-section payment-panel">
      <div>
        <h1 class="page-title">模拟支付</h1>
        <PaymentCountdown :expires-at="order?.expires_at" />
      </div>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="订单号">{{ orderNo || '--' }}</el-descriptions-item>
        <el-descriptions-item label="订单状态">{{ order?.status || '待支付' }}</el-descriptions-item>
        <el-descriptions-item label="应付金额">
          <span class="price mono-num">{{ formatCurrency(order?.total_amount) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="出票数量">{{ order?.tickets.length ?? '--' }}</el-descriptions-item>
      </el-descriptions>
      <div class="actions">
        <el-button type="primary" :loading="loading" @click="pay">确认支付</el-button>
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
