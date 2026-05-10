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
      <el-button type="primary">新增</el-button>
      <el-button>刷新</el-button>
    </div>
    <el-table :data="[]" border>
      <el-table-column v-for="column in columns" :key="column.prop" :prop="column.prop" :label="column.label" :width="column.width" />
      <el-table-column label="操作" width="150" fixed="right">
        <el-button link type="primary">编辑</el-button>
        <el-button link type="danger">删除</el-button>
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
