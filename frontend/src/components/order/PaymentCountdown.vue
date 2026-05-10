<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps<{
  expiresAt?: string | null
}>()

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
  <div class="countdown">
    <span>支付剩余时间</span>
    <strong class="mono-num">{{ display }}</strong>
  </div>
</template>

<style scoped>
.countdown {
  display: inline-flex;
  gap: 10px;
  align-items: center;
  color: var(--fa-text-secondary);
}

strong {
  color: var(--fa-danger);
  font-size: 20px;
}
</style>
