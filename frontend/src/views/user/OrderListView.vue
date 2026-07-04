<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import { orderApi } from '@/api/order'
import { formatCurrency, formatDate } from '@/utils/format'
import { orderStatusLabel, orderStatusOptions } from '@/utils/labels'
import type { OrderListItem, OrderQuery, OrderStatus } from '@/types/order'

const router = useRouter()
const rows = ref<OrderListItem[]>([])
const total = ref(0)
const loading = ref(false)
const query = reactive({
  page: 1,
  page_size: 10,
  status: '' as OrderStatus | '',
})

async function loadOrders() {
  loading.value = true
  const params: OrderQuery = {
    page: query.page,
    page_size: query.page_size,
  }
  if (query.status) {
    params.status = query.status
  }
  try {
    const result = await orderApi.listMine(params)
    rows.value = result.items
    total.value = result.total
    query.page = result.page
    query.page_size = result.page_size
  } finally {
    loading.value = false
  }
}

function handleStatusChange() {
  query.page = 1
  void loadOrders()
}

function handleSizeChange(size: number) {
  query.page_size = size
  query.page = 1
  void loadOrders()
}

function handlePageChange(page: number) {
  query.page = page
  void loadOrders()
}

function statusTagType(status: OrderStatus) {
  const map: Record<OrderStatus, 'success' | 'info' | 'warning' | 'danger'> = {
    待支付: 'warning',
    已支付: 'success',
    已取消: 'info',
    已完成: 'success',
    部分退款: 'warning',
    已完成退款: 'info',
  }
  return map[status]
}

function hasIssuedTickets(status: OrderStatus) {
  return status !== '待支付' && status !== '已取消'
}

onMounted(() => {
  void loadOrders()
})
</script>

<template>
  <div class="page-shell order-list">
    <section class="page-section">
      <div class="toolbar">
        <h1 class="page-title">My Orders</h1>
        <el-select v-model="query.status" class="status-select" @change="handleStatusChange">
          <el-option v-for="item in orderStatusOptions" :key="item.value || 'all'" :label="item.label" :value="item.value" />
        </el-select>
        <el-button @click="loadOrders">Refresh</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" border row-key="order_no">
        <template #empty>
          <EmptyState title="No Orders" description="Your orders will appear here after booking." />
        </template>
        <el-table-column prop="order_no" label="Order No." min-width="210" />
        <el-table-column label="Status" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ orderStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Amount" width="140">
          <template #default="{ row }">{{ formatCurrency(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column label="Created At" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="Quantity" width="110">
          <template #default="{ row }">
            {{ hasIssuedTickets(row.status) ? `Tickets ${row.ticket_count}` : `Reserved ${row.ticket_count}` }}
          </template>
        </el-table-column>
        <el-table-column label="Active" width="90">
          <template #default="{ row }">{{ hasIssuedTickets(row.status) ? row.active_count : '--' }}</template>
        </el-table-column>
        <el-table-column label="Refunded" width="90">
          <template #default="{ row }">{{ hasIssuedTickets(row.status) ? row.refunded_count : '--' }}</template>
        </el-table-column>
        <el-table-column label="Actions" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === '待支付'" link type="primary" @click="router.push(`/payment/${row.order_no}`)">Pay</el-button>
            <el-button link type="primary" @click="router.push(`/orders/${row.order_no}`)">Details</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.order-list {
  padding: 20px 0 8px;
}

.status-select {
  width: 150px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
