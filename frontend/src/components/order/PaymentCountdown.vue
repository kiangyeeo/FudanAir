<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    expiresAt?: string | null
    /** 支付窗口总秒数，用于进度环，默认 15 分钟 */
    totalSeconds?: number
  }>(),
  {
    expiresAt: null,
    totalSeconds: 900,
  },
)

const now = ref(Date.now())
let timer: number | undefined

const remainingSeconds = computed(() => {
  if (!props.expiresAt) {
    return 0
  }
  return Math.max(0, Math.floor((new Date(props.expiresAt).getTime() - now.value) / 1000))
})

const display = computed(() => {
  const minutes = Math.floor(remainingSeconds.value / 60)
  const seconds = remainingSeconds.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const urgent = computed(() => remainingSeconds.value > 0 && remainingSeconds.value <= 120)

const RADIUS = 26
const CIRC = 2 * Math.PI * RADIUS
const dashOffset = computed(() => {
  const ratio = Math.min(1, Math.max(0, remainingSeconds.value / props.totalSeconds))
  return CIRC * (1 - ratio)
})

onMounted(() => {
  timer = window.setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onBeforeUnmount(() => {
  if (timer) {
    window.clearInterval(timer)
  }
})
</script>

<template>
  <div class="countdown" :class="{ urgent }">
    <svg class="ring" viewBox="0 0 60 60" aria-hidden="true">
      <circle class="ring-track" cx="30" cy="30" :r="RADIUS" />
      <circle
        class="ring-progress"
        cx="30"
        cy="30"
        :r="RADIUS"
        :stroke-dasharray="CIRC"
        :stroke-dashoffset="dashOffset"
      />
    </svg>
    <div class="text">
      <span class="label">Payment Time Left</span>
      <strong class="value mono-num">{{ display }}</strong>
    </div>
  </div>
</template>

<style scoped lang="scss">
.countdown {
  display: inline-flex;
  gap: 14px;
  align-items: center;
  padding: 12px 18px;
  border-radius: var(--fa-radius);
  background: var(--fa-brand-soft);
  color: var(--fa-text-secondary);
  transition: background-color var(--fa-dur-base) var(--fa-ease);
}

.countdown.urgent {
  background: var(--fa-promo-soft);
  animation: fa-pulse 1.4s ease-in-out infinite;
}

.ring {
  width: 52px;
  height: 52px;
  transform: rotate(-90deg);
}

.ring-track {
  fill: none;
  stroke: rgba(22, 119, 255, 0.18);
  stroke-width: 5;
}

.ring-progress {
  fill: none;
  stroke: var(--fa-brand);
  stroke-width: 5;
  stroke-linecap: round;
  transition: stroke-dashoffset 1s linear, stroke var(--fa-dur-base) var(--fa-ease);
}

.urgent .ring-track {
  stroke: rgba(245, 34, 45, 0.18);
}

.urgent .ring-progress {
  stroke: var(--fa-promo);
}

.text {
  display: grid;
  gap: 2px;
}

.label {
  font-size: 12px;
}

.value {
  font-size: 24px;
  font-weight: 800;
  color: var(--fa-brand);
  line-height: 1;
}

.urgent .value {
  color: var(--fa-promo);
}
</style>
