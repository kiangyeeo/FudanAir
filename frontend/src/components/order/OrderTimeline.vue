<script setup lang="ts">
import { computed } from 'vue'
import { Wallet, CreditCard, RefreshLeft, Money, Select, CircleClose } from '@element-plus/icons-vue'

const props = defineProps<{
  status: string
}>()

const iconMap: Record<string, unknown> = {
  待支付: Wallet,
  已支付: CreditCard,
  部分退款: RefreshLeft,
  已完成退款: Money,
  已完成: Select,
  已取消: CircleClose,
}

const isCancelled = computed(() => props.status === '已取消')

const steps = computed(() =>
  isCancelled.value ? ['待支付', '已取消'] : ['待支付', '已支付', '部分退款', '已完成退款', '已完成'],
)

const activeIndex = computed(() => Math.max(steps.value.indexOf(props.status), 0))

function nodeState(index: number) {
  if (index < activeIndex.value) {
    return 'done'
  }
  if (index === activeIndex.value) {
    return isCancelled.value && index === steps.value.length - 1 ? 'cancelled' : 'current'
  }
  return 'pending'
}
</script>

<template>
  <div class="timeline" :class="{ cancelled: isCancelled }">
    <div
      v-for="(item, index) in steps"
      :key="item"
      class="step"
      :data-state="nodeState(index)"
    >
      <span v-if="index > 0" class="track" :class="{ filled: index <= activeIndex }" />
      <span class="node">
        <el-icon><component :is="iconMap[item] ?? Wallet" /></el-icon>
      </span>
      <span class="label">{{ item }}</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.timeline {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  padding: 8px 0 4px;
}

.step {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 8px;
}

.track {
  position: absolute;
  top: 18px;
  right: 50%;
  left: -50%;
  height: 3px;
  background: var(--fa-border);
  border-radius: var(--fa-radius-pill);
}

.track.filled {
  background: var(--fa-brand);
}

.node {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--fa-surface-2);
  color: var(--fa-text-tertiary);
  border: 2px solid var(--fa-border);
  font-size: 18px;
  z-index: 1;
  transition: all var(--fa-dur-base) var(--fa-ease);
}

.label {
  font-size: 13px;
  font-weight: 500;
  color: var(--fa-text-tertiary);
}

.step[data-state='done'] .node {
  background: var(--fa-brand-soft);
  border-color: var(--fa-brand);
  color: var(--fa-brand);
}

.step[data-state='done'] .label {
  color: var(--fa-text-secondary);
}

.step[data-state='current'] .node {
  background: var(--fa-grad-brand);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 0 0 4px rgba(22, 119, 255, 0.16);
  animation: fa-pulse 1.8s ease-in-out infinite;
}

.step[data-state='current'] .label {
  color: var(--fa-brand);
  font-weight: 700;
}

.step[data-state='cancelled'] .node {
  background: var(--fa-promo);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 0 0 4px rgba(245, 34, 45, 0.16);
}

.step[data-state='cancelled'] .label {
  color: var(--fa-promo);
  font-weight: 700;
}

.cancelled .track.filled {
  background: var(--fa-promo);
}
</style>
