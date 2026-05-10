<script setup lang="ts">
import AdminTablePlaceholder from './AdminTablePlaceholder.vue'
</script>

<template>
  <AdminTablePlaceholder
    title="机场管理"
    description="新增或修改机场时，后端会通过 AirportService 保持 city_near_apt 双写一致。"
    :columns="[
      { prop: 'iata_code', label: 'IATA', width: 100 },
      { prop: 'airport_name', label: '机场名称' },
      { prop: 'city_name', label: '所属城市', width: 140 },
    ]"
  />
</template>
