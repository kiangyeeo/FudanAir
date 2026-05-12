<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { orderApi } from '@/api/order'
import EmptyState from '@/components/common/EmptyState.vue'
import OrderTimeline from '@/components/order/OrderTimeline.vue'
import { formatCurrency, formatDate, formatTime } from '@/utils/format'
import type { OrderDetail, OrderStatus, OrderTicket } from '@/types/order'

const route = useRoute()
const router = useRouter()
const orderNo = computed(() => String(route.params.orderNo || ''))
const detail = ref<OrderDetail | null>(null)
const loading = ref(false)
const hasIssuedTickets = computed(() => {
  if (!detail.value) {
    return false
  }
  return detail.value.status !== '待支付' && detail.value.status !== '已取消'
})

async function loadDetail() {
  if (!orderNo.value) {
    return
  }
  loading.value = true
  try {
    detail.value = await orderApi.getDetail(orderNo.value)
  } finally {
    loading.value = false
  }
}

function statusTagType(status: OrderStatus | string) {
  const map: Record<string, 'success' | 'info' | 'warning' | 'danger'> = {
    待支付: 'warning',
    已支付: 'success',
    已取消: 'info',
    已完成: 'success',
    部分退款: 'warning',
    已完成退款: 'info',
    有效: 'success',
    已退: 'info',
    已改签作废: 'warning',
    已使用: 'info',
  }
  return map[status] ?? 'info'
}

function refund(ticket: OrderTicket) {
  router.push({ name: 'refund', query: { ticket_no: ticket.ticket_no } })
}

function change(ticket: OrderTicket) {
  router.push({ name: 'change', query: { ticket_no: ticket.ticket_no } })
}

onMounted(() => {
  void loadDetail()
})
</script>

<template>
  <div class="page-shell order-detail">
    <section v-loading="loading" class="page-section">
      <h1 class="page-title">订单详情</h1>
      <template v-if="detail">
        <OrderTimeline :status="detail.status" />
        <el-descriptions :column="3" border class="summary">
          <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType(detail.status)">{{ detail.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="金额">{{ formatCurrency(detail.total_amount) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="用户 ID">{{ detail.user_id }}</el-descriptions-item>
          <el-descriptions-item :label="hasIssuedTickets ? '客票数' : '锁座人数'">{{ detail.tickets.length }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <EmptyState v-else title="暂无订单详情" :description="`当前订单号：${orderNo || '--'}`" />
    </section>

    <section class="page-section">
      <h2>{{ hasIssuedTickets ? '客票' : '锁座信息' }}</h2>
      <el-alert
        v-if="detail && !hasIssuedTickets"
        type="info"
        show-icon
        :closable="false"
        title="订单未支付完成，暂不展示客票号和退改入口。支付成功后再查看客票。"
      />
      <el-table v-else :data="detail?.tickets ?? []" border row-key="ticket_no">
        <el-table-column prop="ticket_no" label="票号" min-width="180" />
        <el-table-column label="乘机人" min-width="160">
          <template #default="{ row }">
            <div>{{ row.passenger.real_name }}</div>
            <span class="subtle">{{ row.passenger.id_no }}</span>
          </template>
        </el-table-column>
        <el-table-column label="航班" min-width="180">
          <template #default="{ row }">
            <div>{{ row.flight_no }} · {{ row.instance_id }}</div>
            <span class="subtle">{{ row.dep_airport_code }} → {{ row.arr_airport_code }}</span>
          </template>
        </el-table-column>
        <el-table-column label="日期时间" min-width="170">
          <template #default="{ row }">
            <div>{{ formatDate(row.flight_date) }}</div>
            <span class="subtle">{{ formatTime(row.scheduled_departure) }} - {{ formatTime(row.scheduled_arrival) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="舱位票价" min-width="130">
          <template #default="{ row }">
            <div>{{ row.cabin_class }} · {{ row.fare_type }}</div>
            <span class="price mono-num">{{ formatCurrency(row.actual_price) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === '有效'" link type="primary" @click="refund(row)">退票</el-button>
            <el-button v-if="row.status === '有效'" link type="primary" @click="change(row)">改签</el-button>
            <span v-else class="subtle">不可操作</span>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped lang="scss">
.order-detail {
  display: grid;
  gap: 16px;
}

.summary {
  margin-top: 14px;
}

h2 {
  margin: 0 0 12px;
  font-size: 16px;
}

.subtle {
  color: var(--fa-text-secondary);
  font-size: 12px;
}

.price {
  color: var(--fa-danger);
  font-weight: 600;
}
</style>
