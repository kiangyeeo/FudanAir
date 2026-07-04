<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { orderApi } from '@/api/order'
import { formatCurrency, formatDate } from '@/utils/format'
import { orderStatusLabel, orderStatusOptions } from '@/utils/labels'
import type { AdminOrderQuery, OrderListItem, OrderStatus } from '@/types/order'

const rows = ref<OrderListItem[]>([])
const total = ref(0)
const loading = ref(false)
const userId = ref<number>()
const dateRange = ref<[string, string] | []>([])
const query = reactive({
  page: 1,
  page_size: 10,
  status: '' as OrderStatus | '',
})


async function loadOrders() {
  loading.value = true
  const [dateFrom, dateTo] = dateRange.value
  const params: AdminOrderQuery = {
    page: query.page,
    page_size: query.page_size,
  }

  if (query.status) {
    params.status = query.status
  }
  if (userId.value !== undefined) {
    params.user_id = userId.value
  }
  if (dateFrom && dateTo) {
    params.date_from = dateFrom
    params.date_to = dateTo
  }

  try {
    const result = await orderApi.listAdmin(params)
    rows.value = result.items
    total.value = result.total
    query.page = result.page
    query.page_size = result.page_size
  } finally {
    loading.value = false
  }
}

function submitFilters() {
  query.page = 1
  void loadOrders()
}

function resetFilters() {
  query.status = ''
  userId.value = undefined
  dateRange.value = []
  submitFilters()
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

function hasAffectedInstance(row: OrderListItem) {
  return Number(row.affected_instance_count ?? 0) > 0
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

onMounted(() => {
  void loadOrders()
})
</script>

<template>
  <section class="page-section admin-orders">
    <div class="page-heading">
      <h1 class="page-title">Orders</h1>
      <span class="subtle">Read-only access to all orders</span>
    </div>

    <el-form class="filter-bar" inline @submit.prevent>
      <el-form-item label="Status">
        <el-select v-model="query.status" class="status-select" @change="submitFilters">
          <el-option v-for="item in orderStatusOptions" :key="item.value || 'all'" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="User ID">
        <el-input-number v-model="userId" :min="1" :controls="false" placeholder="All users" class="user-id-input" />
      </el-form-item>
      <el-form-item label="Created Date">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="Start date"
          end-placeholder="End date"
          range-separator="to"
          class="date-range"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="submitFilters">Search</el-button>
        <el-button :icon="Refresh" @click="resetFilters">Reset</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="rows" border row-key="order_no">
      <template #empty>
        <span>No Orders</span>
      </template>
      <el-table-column prop="order_no" label="Order No." min-width="220" />
      <el-table-column label="User" min-width="150">
        <template #default="{ row }">
          <div>{{ row.user_name || '--' }}</div>
          <span class="subtle">ID {{ row.user_id }}</span>
        </template>
      </el-table-column>
      <el-table-column label="Status" width="120">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)">{{ orderStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Amount" width="140">
        <template #default="{ row }">{{ formatCurrency(row.total_amount) }}</template>
      </el-table-column>
      <el-table-column label="Created At" min-width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="ticket_count" label="Tickets" width="100" />
      <el-table-column prop="active_count" label="Active" width="100" />
      <el-table-column prop="refunded_count" label="Refunded" width="100" />
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
</template>

<style scoped>
.admin-orders {
  display: grid;
  gap: 14px;
}

.page-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
}

.status-select {
  width: 150px;
}

.user-id-input {
  width: 150px;
}

.date-range {
  width: 260px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
}

.subtle {
  color: var(--fa-text-secondary);
  font-size: 12px;
}
</style>
