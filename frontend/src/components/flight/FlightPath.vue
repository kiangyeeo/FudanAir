<script setup lang="ts">
import { computed } from 'vue'
import { formatDuration } from '@/utils/format'

const props = withDefaults(
  defineProps<{
    /** 行程总时长（分钟）；为空则不显示时长 */
    duration?: number | null
    /** 经停/中转次数，0 表示直飞 */
    stops?: number
    /** 中转节点说明，如 "中转 PEK · 1小时30分"；提供时覆盖默认经停文案 */
    stopLabel?: string | null
    compact?: boolean
  }>(),
  {
    duration: null,
    stops: 0,
    stopLabel: null,
    compact: false,
  },
)

const durationText = computed(() => (props.duration != null ? formatDuration(props.duration) : ''))
const stopText = computed(() => {
  if (props.stopLabel) {
    return props.stopLabel
  }
  return props.stops > 0 ? `${props.stops} stop${props.stops > 1 ? 's' : ''}` : 'Nonstop'
})
const isDirect = computed(() => props.stops === 0 && !props.stopLabel)
</script>

<template>
  <div class="flight-path" :class="{ compact }">
    <span v-if="durationText" class="duration mono-num">{{ durationText }}</span>
    <div class="track">
      <span class="dot start" />
      <span class="line">
        <span v-if="!isDirect" class="stop-node" />
        <svg class="plane" viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2A1.5 1.5 0 0 0 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1l3.5 1v-1.5L13 19v-5.5z"
          />
        </svg>
      </span>
      <span class="dot end" />
    </div>
    <span class="stop-text" :class="{ direct: isDirect }">{{ stopText }}</span>
  </div>
</template>

<style scoped lang="scss">
.flight-path {
  display: grid;
  justify-items: center;
  gap: 8px;
  min-width: 0;
}

.compact {
  gap: 4px;
}

.duration {
  color: var(--fa-text-secondary);
  font-size: 14px;
  font-weight: 600;
}

.track {
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 120px;
}

.dot {
  flex: 0 0 auto;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 1.5px solid var(--fa-brand);
  background: var(--fa-white);
}

.line {
  position: relative;
  flex: 1 1 auto;
  height: 0;
  border-top: 1.5px dashed var(--fa-border-strong);
  margin: 0 2px;
}

.stop-node {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--fa-accent);
  transform: translate(-50%, -50%);
}

.plane {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 24px;
  height: 24px;
  color: var(--fa-brand);
  transform: translate(-50%, -50%) rotate(90deg);
}

.stop-text {
  font-size: 14px;
  font-weight: 700;
  color: var(--fa-accent);
}

.stop-text.direct {
  color: var(--fa-success);
}

/* 紧凑模式（预订摘要等）保持较小尺寸 */
.compact .track {
  min-width: 72px;
}

.compact .duration {
  font-size: 12px;
}

.compact .plane {
  width: 16px;
  height: 16px;
}

.compact .stop-text {
  font-size: 11px;
  font-weight: 600;
}

.compact .dot {
  width: 7px;
  height: 7px;
}
</style>
