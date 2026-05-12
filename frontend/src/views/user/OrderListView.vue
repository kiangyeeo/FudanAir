<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { orderApi } from '@/api/order'
import { formatCurrency, formatDate } from '@/utils/format'
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

onMounted(() => {
  void loadOrders()
})
</script>

<template>
  <div class="page-shell">
    <section class="page-section">
      <div class="toolbar">
        <h1 class="page-title">我的订单</h1>
        <el-select v-model="query.status" class="status-select" @change="handleStatusChange">
          <el-option v-for="item in statusOptions" :key="item.value || 'all'" :label="item.label" :value="item.value" />
        </el-select>
        <el-button @click="loadOrders">刷新</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" border row-key="order_no">
        <template #empty>
          <span>暂无订单</span>
        </template>
        <el-table-column prop="order_no" label="订单号" min-width="210" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="140">
          <template #default="{ row }">{{ formatCurrency(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="ticket_count" label="票数" width="90" />
        <el-table-column prop="active_count" label="有效票" width="90" />
        <el-table-column prop="refunded_count" label="已退票" width="90" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === '待支付'" link type="primary" @click="router.push(`/payment/${row.order_no}`)">支付</el-button>
            <el-button link type="primary" @click="router.push(`/orders/${row.order_no}`)">详情</el-button>
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
.status-select {
  width: 150px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
