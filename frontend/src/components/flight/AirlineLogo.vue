<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    code: string
    name?: string | null
    size?: number
  }>(),
  {
    name: null,
    size: 36,
  },
)

const extensions = ['svg', 'png', 'webp', 'jpg'] as const
const extensionIndex = ref(0)
const failed = ref(false)
const normalizedCode = computed(() => props.code.trim().toUpperCase())
const label = computed(() => props.name || normalizedCode.value)
const logoSrc = computed(() => `/images/airlines/${normalizedCode.value}.${extensions[extensionIndex.value]}`)
const logoStyle = computed(() => ({
  '--airline-logo-size': `${props.size}px`,
}))

watch(normalizedCode, () => {
  extensionIndex.value = 0
  failed.value = false
})

function handleError() {
  if (extensionIndex.value < extensions.length - 1) {
    extensionIndex.value += 1
    return
  }
  failed.value = true
}
</script>

<template>
  <div class="airline-logo" :style="logoStyle" :title="label" :aria-label="label">
    <img v-if="!failed" :src="logoSrc" :alt="label" loading="lazy" @error="handleError" />
    <span v-else>{{ normalizedCode }}</span>
  </div>
</template>

<style scoped lang="scss">
.airline-logo {
  display: inline-grid;
  place-items: center;
  width: var(--airline-logo-size);
  height: var(--airline-logo-size);
  flex: 0 0 var(--airline-logo-size);
}

img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

span {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  border: 1px solid var(--fa-border);
  border-radius: 50%;
  color: var(--fa-text-secondary);
  background: var(--fa-bg);
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
}
</style>
