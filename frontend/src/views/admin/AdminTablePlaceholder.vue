<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import type { AdminTableColumn } from '@/types/admin'

defineProps<{
  title: string
  description: string
  columns: AdminTableColumn[]
}>()
</script>

<template>
  <section class="page-section admin-table">
    <div class="toolbar">
      <h1 class="page-title">{{ title }}</h1>
      <el-button type="primary">Add</el-button>
      <el-button>Refresh</el-button>
    </div>
    <el-table :data="[]" border>
      <el-table-column v-for="column in columns" :key="column.prop" :prop="column.prop" :label="column.label" :width="column.width" />
      <el-table-column label="Actions" width="150" fixed="right">
        <el-button link type="primary">Edit</el-button>
        <el-button link type="danger">Delete</el-button>
      </el-table-column>
    </el-table>
    <EmptyState :title="title" :description="description" />
  </section>
</template>

<style scoped>
.admin-table {
  display: grid;
  gap: 12px;
}
</style>
