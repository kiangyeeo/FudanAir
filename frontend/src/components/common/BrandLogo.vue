<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 徽标圆形尺寸（px） */
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
    <img
      class="mark"
      :style="{ width: `${size}px`, height: `${size}px` }"
      src="/images/brand-emblem.png"
      alt="FudanAir"
    />
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
  flex: 0 0 auto;
  border-radius: 50%;
  object-fit: cover;
  background: #fff;
  box-shadow: 0 1px 4px rgba(20, 45, 85, 0.18);
}

.inverse .mark {
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.5), 0 2px 8px rgba(0, 0, 0, 0.25);
}

.text {
  font-family: var(--fa-font-serif);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0;
  color: var(--fa-text);
}

.inverse .text {
  color: var(--fa-text-inverse);
}
</style>
