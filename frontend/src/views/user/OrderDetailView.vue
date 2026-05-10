<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import OrderTimeline from '@/components/order/OrderTimeline.vue'
import { formatCurrency } from '@/utils/format'
import type { OrderDetail } from '@/types/order'

const route = useRoute()
const orderNo = computed(() => String(route.params.orderNo || ''))
const detail = ref<OrderDetail | null>(null)
</script>

<template>
  <div class="page-shell order-detail">
    <section class="page-section">
      <h1 class="page-title">订单详情</h1>
      <template v-if="detail">
        <OrderTimeline :status="detail.status" />
        <el-descriptions :column="3" border>
          <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ detail.status }}</el-descriptions-item>
          <el-descriptions-item label="金额">{{ formatCurrency(detail.total_amount) }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <EmptyState v-else title="订单详情占位" :description="`当前订单号：${orderNo || '--'}。后端订单接口接入后会展示客票明细。`" />
    </section>

    <section class="page-section">
      <h2>客票</h2>
      <el-table :data="detail?.tickets ?? []" border>
        <el-table-column prop="ticket_no" label="票号" min-width="180" />
        <el-table-column prop="passenger.real_name" label="乘机人" width="120" />
        <el-table-column prop="flight_no" label="航班号" width="120" />
        <el-table-column prop="flight_date" label="日期" width="130" />
        <el-table-column prop="status" label="状态" width="110" />
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.order-detail {
  display: grid;
  gap: 16px;
}

h2 {
  margin: 0 0 12px;
  font-size: 16px;
}
</style>
