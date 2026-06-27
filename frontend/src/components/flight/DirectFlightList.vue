<script setup lang="ts">
import { computed } from 'vue'
import EmptyState from '@/components/common/EmptyState.vue'
import FlightCard from './FlightCard.vue'
import type { DirectFlightCandidate } from '@/types/search'

const props = defineProps<{
  items: DirectFlightCandidate[]
}>()

const emit = defineEmits<{
  select: [candidate: DirectFlightCandidate]
}>()

const lowestId = computed(() => {
  if (!props.items.length) {
    return null
  }
  return props.items.reduce((min, item) => (item.min_price < min.min_price ? item : min)).instance_id
})
</script>

<template>
  <section class="flight-list">
    <header class="list-head">
      <span class="dot direct" />
      <h2>直飞航班</h2>
      <span class="count">{{ items.length }} 个方案</span>
    </header>
    <template v-if="items.length">
      <FlightCard
        v-for="(item, index) in items"
        :key="item.instance_id"
        :candidate="item"
        :lowest="item.instance_id === lowestId"
        v-motion
        :initial="{ opacity: 0, y: 14 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 320, delay: index * 55 } }"
        @select="emit('select', item)"
      />
    </template>
    <EmptyState v-else title="暂无直飞航班" description="可查看中转或临近机场替代方案。" />
  </section>
</template>

<style scoped lang="scss">
.flight-list {
  display: grid;
  gap: 12px;
}

.list-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.list-head h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--fa-brand);
}

.dot.direct {
  background: var(--fa-brand);
}

.count {
  color: var(--fa-text-tertiary);
  font-size: 13px;
}
</style>
