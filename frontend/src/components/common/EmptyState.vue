<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    description?: string
  }>(),
  {
    title: '暂无数据',
    description: '当前模块已预留接口与页面结构，等待业务数据接入。',
  },
)
</script>

<template>
  <div class="empty-state">
    <svg class="empty-art" viewBox="0 0 120 88" aria-hidden="true">
      <ellipse cx="60" cy="78" rx="42" ry="6" fill="rgba(20,45,85,0.06)" />
      <path d="M18 46c8-3 18-2 26 2" fill="none" stroke="var(--fa-border-strong)" stroke-width="2" stroke-linecap="round" opacity="0.7" />
      <path d="M84 30c10-2 18 1 22 6" fill="none" stroke="var(--fa-border-strong)" stroke-width="2" stroke-linecap="round" opacity="0.5" />
      <g class="art-plane">
        <path
          fill="var(--fa-brand)"
          d="M92 40v-4l-22-13V8a4 4 0 0 0-8 0v15L40 36v4l22-7v15l-6 4v3l10-3l10 3v-3l-6-4V33z"
          transform="rotate(8 66 36)"
        />
      </g>
    </svg>
    <p class="empty-title">{{ title }}</p>
    <p class="empty-description">{{ description }}</p>
  </div>
</template>

<style scoped lang="scss">
.empty-state {
  display: grid;
  justify-items: center;
  gap: 6px;
  padding: 32px 16px;
  text-align: center;
}

.empty-art {
  width: 132px;
  height: auto;
}

.art-plane {
  transform-origin: 66px 36px;
  animation: fa-float 4s ease-in-out infinite;
}

.empty-title {
  margin: 8px 0 0;
  color: var(--fa-text);
  font-size: 15px;
  font-weight: 600;
}

.empty-description {
  margin: 0;
  color: var(--fa-text-tertiary);
  font-size: 13px;
  max-width: 320px;
}
</style>
