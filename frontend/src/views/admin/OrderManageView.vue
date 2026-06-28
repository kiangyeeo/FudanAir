<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { orderApi } from '@/api/order'
import { formatCurrency, formatDate } from '@/utils/format'
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

const statusOptions: Array<{ label: string; value: OrderStatus | '' }> = [
  { label: '全部状态', value: '' },
  { label: '待支付', value: '待支付' },
  { label: '已支付', value: '已支付' },
  { label: '已取消', value: '已取消' },
  { label: '已完成', value: '已完成' },
  { label: '部分退款', value: '部分退款' },
  { label: '已完成退款', value: '已完成退款' },
]

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
      <h1 class="page-title">订单查询</h1>
      <span class="subtle">管理员只读查看全部订单</span>
    </div>

    <el-form class="filter-bar" inline @submit.prevent>
      <el-form-item label="状态">
        <el-select v-model="query.status" class="status-select" @change="submitFilters">
          <el-option v-for="item in statusOptions" :key="item.value || 'all'" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="用户 ID">
        <el-input-number v-model="userId" :min="1" :controls="false" placeholder="全部用户" class="user-id-input" />
      </el-form-item>
      <el-form-item label="创建日期">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          range-separator="至"
          class="date-range"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="submitFilters">查询</el-button>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="rows" border row-key="order_no">
      <template #empty>
        <span>暂无订单</span>
      </template>
      <el-table-column prop="order_no" label="订单号" min-width="220" />
      <el-table-column label="用户" min-width="150">
        <template #default="{ row }">
          <div>{{ row.user_name || '--' }}</div>
          <span class="subtle">ID {{ row.user_id }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="订单金额" width="140">
        <template #default="{ row }">{{ formatCurrency(row.total_amount) }}</template>
      </el-table-column>
      <el-table-column label="创建时间" min-width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="ticket_count" label="客票数" width="100" />
      <el-table-column prop="active_count" label="有效票" width="100" />
      <el-table-column prop="refunded_count" label="已退票" width="100" />
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
