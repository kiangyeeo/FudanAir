<script setup lang="ts">
import AdminTablePlaceholder from './AdminTablePlaceholder.vue'
</script>

<template>
  <AdminTablePlaceholder
    title="实例管理"
    description="维护具体日期的航班实例和状态。"
    :columns="[
      { prop: 'instance_id', label: '实例 ID', width: 180 },
      { prop: 'flight_no', label: '航班号', width: 120 },
      { prop: 'flight_date', label: '日期', width: 130 },
      { prop: 'status', label: '状态', width: 110 },
      { prop: 'economy_left', label: '经济舱余票', width: 130 },
      { prop: 'first_left', label: '头等舱余票', width: 130 },
    ]"
  />
</template>
