<script setup lang="ts">
import AdminTablePlaceholder from './AdminTablePlaceholder.vue'
</script>

<template>
  <AdminTablePlaceholder
    title="票价管理"
    description="维护航班实例下的舱位、票价类型、价格和可售库存。"
    :columns="[
      { prop: 'instance_id', label: '实例 ID', width: 180 },
      { prop: 'cabin_class', label: '舱位', width: 110 },
      { prop: 'fare_type', label: '票价类型', width: 120 },
      { prop: 'price', label: '价格', width: 120 },
      { prop: 'available_seats', label: '可售座位', width: 130 },
    ]"
  />
</template>
