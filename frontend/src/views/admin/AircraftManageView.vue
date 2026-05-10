<script setup lang="ts">
import AdminTablePlaceholder from './AdminTablePlaceholder.vue'
</script>

<template>
  <AdminTablePlaceholder
    title="机型管理"
    description="维护机型座位配置。"
    :columns="[
      { prop: 'model', label: '机型', width: 140 },
      { prop: 'economy_seats', label: '经济舱座位', width: 140 },
      { prop: 'first_seats', label: '头等舱座位', width: 140 },
    ]"
  />
</template>
