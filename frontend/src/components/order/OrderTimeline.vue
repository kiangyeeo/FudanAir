<script setup lang="ts">
const props = defineProps<{
  status: string
}>()

const steps = ['待支付', '已支付', '部分退款', '已完成退款', '已完成']

function statusType(item: string) {
  return props.status === item ? 'primary' : 'info'
}
</script>

<template>
  <el-steps :active="Math.max(steps.indexOf(status), 0)" finish-status="success" simple>
    <el-step v-for="item in steps" :key="item" :title="item" :status="statusType(item)" />
  </el-steps>
</template>
