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

function nearbyTag(item: NearbyFlightCandidate) {
  const side = item.replacement === 'departure' ? '替换出发' : '替换到达'
  return `临近 · ${side} ${item.replaced_airport}`
}
</script>

<template>
  <section class="flight-list">
    <header class="list-head">
      <span class="dot" />
      <h2>临近机场方案</h2>
      <span class="count">{{ items.length }} 个方案</span>
    </header>
    <template v-if="items.length">
      <FlightCard
        v-for="(item, index) in items"
        :key="`${item.replacement}-${item.instance_id}`"
        :candidate="item"
        :nearby-tag="nearbyTag(item)"
        v-motion
        :initial="{ opacity: 0, y: 14 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 320, delay: index * 55 } }"
        @select="emit('select', item)"
      />
    </template>
    <EmptyState v-else title="暂无临近机场方案" description="系统会按城市临近机场关系补充替代路线。" />
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
  background: var(--fa-accent);
}

.count {
  color: var(--fa-text-tertiary);
  font-size: 13px;
}
</style>
