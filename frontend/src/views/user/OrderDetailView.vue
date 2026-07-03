<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { orderApi } from '@/api/order'
import EmptyState from '@/components/common/EmptyState.vue'
import OrderTimeline from '@/components/order/OrderTimeline.vue'
import { formatCurrency, formatDate, formatTime, maskIdNo } from '@/utils/format'
import { adjustmentLabel, cabinClassLabel, fareTypeLabel, instanceStatusLabel, orderStatusLabel, ticketStatusLabel } from '@/utils/labels'
import { useAirportStore } from '@/stores/airport'
import type { OrderDetail, OrderStatus, OrderTicket } from '@/types/order'

const route = useRoute()
const router = useRouter()
const airportStore = useAirportStore()
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

const affectedTickets = computed(() =>
  (detail.value?.tickets ?? []).filter((ticket) => ticket.status === '有效' && ticket.flight_instance_status !== '可订'),
)

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
  router.push({ name: 'refund', query: { ticket_no: ticket.ticket_no, order_no: orderNo.value } })
}

function change(ticket: OrderTicket) {
  router.push({ name: 'change', query: { ticket_no: ticket.ticket_no, order_no: orderNo.value } })
}

onMounted(() => {
  void airportStore.ensureLoaded()
  void loadDetail()
})
</script>

<template>
  <div class="page-shell order-detail">
    <section v-loading="loading" class="page-section">
      <h1 class="page-title">Order Details</h1>
      <template v-if="detail">
        <OrderTimeline :status="detail.status" />
        <el-alert
          v-if="affectedTickets.length"
          type="warning"
          show-icon
          :closable="false"
          class="status-alert"
          :title="`${affectedTickets.length} active ticket(s) are linked to flight instances that are no longer bookable. Check flight status.`"
        />
        <el-descriptions :column="3" border class="summary">
          <el-descriptions-item label="Order No.">{{ detail.order_no }}</el-descriptions-item>
          <el-descriptions-item label="Status">
            <el-tag :type="statusTagType(detail.status)">{{ orderStatusLabel(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Amount">{{ formatCurrency(detail.total_amount) }}</el-descriptions-item>
          <el-descriptions-item label="Created At">{{ formatDate(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="User ID">{{ detail.user_id }}</el-descriptions-item>
          <el-descriptions-item :label="hasIssuedTickets ? 'Tickets' : 'Reserved Seats'">{{ detail.tickets.length }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <EmptyState v-else title="No Order Details" :description="`Current order no.: ${orderNo || '--'}`" />
    </section>

    <section class="page-section">
      <h2>{{ hasIssuedTickets ? 'Tickets' : 'Reserved Seats' }}</h2>
      <el-alert
        v-if="detail && !hasIssuedTickets"
        type="info"
        show-icon
        :closable="false"
        title="This order is not paid yet. Ticket numbers and refund/change actions will be available after payment."
      />
      <el-table v-else :data="detail?.tickets ?? []" border row-key="ticket_no">
        <el-table-column prop="ticket_no" label="Ticket No." min-width="180" />
        <el-table-column label="Passenger" min-width="160">
          <template #default="{ row }">
            <div>{{ row.passenger.real_name }}</div>
            <span class="subtle mono-num">{{ maskIdNo(row.passenger.id_no) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Flight" min-width="180">
          <template #default="{ row }">
            <div class="flight-line">
              <span class="mono-num">{{ row.flight_no }}</span>
              <el-tag v-if="row.flight_instance_status && row.flight_instance_status !== '可订'" size="small" :type="statusTagType(row.flight_instance_status)">
                {{ instanceStatusLabel(row.flight_instance_status) }}
              </el-tag>
              <el-tag
                v-for="label in row.adjustment_labels ?? []"
                :key="label"
                size="small"
                type="warning"
              >
                {{ adjustmentLabel(label) }}
              </el-tag>
            </div>
            <span class="subtle">{{ airportStore.display(row.dep_airport_code) }} → {{ airportStore.display(row.arr_airport_code) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Date & Time" min-width="170">
          <template #default="{ row }">
            <div>{{ formatDate(row.flight_date) }}</div>
            <span class="subtle">{{ formatTime(row.scheduled_departure) }} - {{ formatTime(row.scheduled_arrival) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Cabin & Fare" min-width="230">
          <template #default="{ row }">
            <div>{{ cabinClassLabel(row.cabin_class) }} · {{ fareTypeLabel(row.fare_type) }}</div>
            <span class="subtle mono-num">
              Ticket {{ formatCurrency(row.ticket_price) }} + Fuel & airport fee {{ formatCurrency(row.fuel_infra_fee) }}
            </span>
            <div class="price mono-num">{{ formatCurrency(row.actual_price) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="Status" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ ticketStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="140" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === '有效'" link type="primary" @click="refund(row)">Refund</el-button>
            <el-button v-if="row.status === '有效'" link type="primary" @click="change(row)">Change</el-button>
            <span v-else class="subtle">Unavailable</span>
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
  padding: 20px 0 8px;
}

.summary {
  margin-top: 14px;
}

.status-alert {
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

.flight-line {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.price {
  color: var(--fa-danger);
  font-weight: 600;
}
</style>
