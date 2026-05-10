<script setup lang="ts">
import AdminTablePlaceholder from './AdminTablePlaceholder.vue'
</script>

<template>
  <AdminTablePlaceholder
    title="航司管理"
    description="维护航空公司基础数据。"
    :columns="[
      { prop: 'iata_code', label: '航司代码', width: 120 },
      { prop: 'airline_name', label: '航司名称' },
    ]"
  />
</template>
