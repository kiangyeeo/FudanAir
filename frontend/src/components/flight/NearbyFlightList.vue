<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import FlightCard from './FlightCard.vue'
import type { NearbyFlightCandidate } from '@/types/search'

defineProps<{
  items: NearbyFlightCandidate[]
}>()

const emit = defineEmits<{
  select: [candidate: NearbyFlightCandidate]
}>()
</script>

<template>
  <section class="flight-list">
    <h2>临近机场方案</h2>
    <template v-if="items.length">
      <div v-for="item in items" :key="`${item.replacement}-${item.instance_id}`" class="nearby-item">
        <el-tag size="small" type="warning">{{ item.replacement === 'departure' ? '替换出发机场' : '替换到达机场' }}</el-tag>
        <FlightCard :candidate="item" @select="emit('select', item)" />
      </div>
    </template>
    <EmptyState v-else title="暂无临近机场方案" description="系统会按城市临近机场关系补充替代路线。" />
  </section>
</template>

<style scoped>
.flight-list,
.nearby-item {
  display: grid;
  gap: 10px;
}

h2 {
  margin: 0;
  font-size: 16px;
}
</style>
