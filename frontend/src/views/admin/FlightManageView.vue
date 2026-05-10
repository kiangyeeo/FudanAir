<script setup lang="ts">
import AdminTablePlaceholder from './AdminTablePlaceholder.vue'
</script>

<template>
  <AdminTablePlaceholder
    title="航班管理"
    description="维护抽象航班、经停和每周飞行日。"
    :columns="[
      { prop: 'flight_no', label: '航班号', width: 120 },
      { prop: 'airline_code', label: '航司', width: 100 },
      { prop: 'dep_airport_code', label: '出发机场', width: 120 },
      { prop: 'arr_airport_code', label: '到达机场', width: 120 },
      { prop: 'scheduled_departure', label: '起飞时间', width: 120 },
      { prop: 'scheduled_arrival', label: '到达时间', width: 120 },
    ]"
  />
</template>
