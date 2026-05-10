<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    description?: string
  }>(),
  {
    title: '暂无数据',
    description: '当前模块已预留接口与页面结构，等待业务数据接入。',
  },
)
</script>

<template>
  <el-empty :description="title">
    <p class="empty-description">{{ description }}</p>
  </el-empty>
</template>

<style scoped>
.empty-description {
  margin: 0;
  color: var(--fa-text-secondary);
  font-size: 13px;
}
</style>
