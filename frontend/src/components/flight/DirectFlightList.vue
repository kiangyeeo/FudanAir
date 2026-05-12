<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import FlightCard from './FlightCard.vue'
import type { DirectFlightCandidate } from '@/types/search'

defineProps<{
  items: DirectFlightCandidate[]
}>()

const emit = defineEmits<{
  select: [candidate: DirectFlightCandidate]
}>()
</script>

<template>
  <section class="flight-list">
    <h2>直飞航班</h2>
    <template v-if="items.length">
      <FlightCard v-for="item in items" :key="item.instance_id" :candidate="item" @select="emit('select', item)" />
    </template>
    <EmptyState v-else title="暂无直飞航班" description="可查看中转或临近机场替代方案。" />
  </section>
</template>

<style scoped>
.flight-list {
  display: grid;
  gap: 10px;
}

h2 {
  margin: 0;
  font-size: 16px;
}
</style>
