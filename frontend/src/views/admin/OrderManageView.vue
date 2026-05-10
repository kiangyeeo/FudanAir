<script setup lang="ts">
import AdminTablePlaceholder from './AdminTablePlaceholder.vue'
</script>

<template>
  <AdminTablePlaceholder
    title="订单查询"
    description="管理员只读查询所有订单。"
    :columns="[
      { prop: 'order_no', label: '订单号', width: 220 },
      { prop: 'user_id', label: '用户 ID', width: 120 },
      { prop: 'status', label: '状态', width: 120 },
      { prop: 'total_amount', label: '金额', width: 120 },
      { prop: 'created_at', label: '创建时间', width: 180 },
    ]"
  />
</template>
