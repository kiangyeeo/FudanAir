<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    value: number
    duration?: number
    /** 小数位 */
    decimals?: number
    prefix?: string
  }>(),
  {
    duration: 900,
    decimals: 0,
    prefix: '',
  },
)

const display = ref(0)
let raf: number | undefined

function animate(to: number) {
  if (raf) {
    cancelAnimationFrame(raf)
  }
  const from = display.value
  const start = performance.now()
  const step = (now: number) => {
    const progress = Math.min(1, (now - start) / props.duration)
    const eased = 1 - Math.pow(1 - progress, 3)
    display.value = from + (to - from) * eased
    if (progress < 1) {
      raf = requestAnimationFrame(step)
    } else {
      display.value = to
    }
  }
  raf = requestAnimationFrame(step)
}

watch(
  () => props.value,
  (next) => animate(next),
  { immediate: true },
)

onBeforeUnmount(() => {
  if (raf) {
    cancelAnimationFrame(raf)
  }
})
</script>

<template>
  <span class="mono-num">{{ prefix }}{{ display.toFixed(decimals) }}</span>
</template>
