<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 标志方块尺寸（px） */
    size?: number
    /** 是否显示 FudanAir 文字 */
    showText?: boolean
    /** 文字内容 */
    text?: string
    /** 文字色是否反白（用于深色背景） */
    inverse?: boolean
  }>(),
  {
    size: 34,
    showText: true,
    text: 'FudanAir',
    inverse: false,
  },
)
</script>

<template>
  <span class="brand-logo" :class="{ inverse }">
    <span class="mark" :style="{ width: `${size}px`, height: `${size}px` }">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          fill="#ffffff"
          d="M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2A1.5 1.5 0 0 0 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1l3.5 1v-1.5L13 19v-5.5z"
        />
      </svg>
    </span>
    <span v-if="showText" class="text">{{ text }}</span>
  </span>
</template>

<style scoped lang="scss">
.brand-logo {
  display: inline-flex;
  align-items: center;
  gap: 9px;
}

.mark {
  display: inline-grid;
  place-items: center;
  flex: 0 0 auto;
  background: var(--fa-grad-brand);
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.32);
}

.mark svg {
  width: 62%;
  height: 62%;
  transform: rotate(18deg);
}

.text {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--fa-text);
}

.inverse .text {
  color: var(--fa-text-inverse);
}
</style>
