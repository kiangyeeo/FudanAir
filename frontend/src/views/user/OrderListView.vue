<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { orderApi } from '@/api/order'
import EmptyState from '@/components/common/EmptyState.vue'
import { formatCurrency, formatDate } from '@/utils/format'
import type { OrderListItem } from '@/types/order'

const router = useRouter()
const loading = ref(false)
const rows = ref<OrderListItem[]>([])

async function load() {
  loading.value = true
  try {
    const data = await orderApi.listMine({ page: 1, page_size: 20 })
    rows.value = data.items
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="page-shell">
    <section class="page-section">
      <div class="toolbar">
        <h1 class="page-title">我的订单</h1>
        <el-button :loading="loading" @click="load">刷新</el-button>
      </div>
      <el-table v-if="rows.length" :data="rows" border>
        <el-table-column prop="order_no" label="订单号" min-width="210" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column label="金额" width="140">
          <template #default="{ row }">{{ formatCurrency(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="ticket_count" label="票数" width="90" />
        <el-table-column label="操作" width="110">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/orders/${row.order_no}`)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else title="暂无订单" description="完成下单后，订单会显示在这里。" />
    </section>
  </div>
</template>
