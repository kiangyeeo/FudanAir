<script setup lang="ts">
import AdminTablePlaceholder from './AdminTablePlaceholder.vue'
</script>

<template>
  <AdminTablePlaceholder
    title="城市管理"
    description="用于维护 city 表和临近机场关系入口。"
    :columns="[
      { prop: 'city_name', label: '城市名称' },
      { prop: 'near_airports', label: '临近机场数量', width: 140 },
    ]"
  />
</template>
