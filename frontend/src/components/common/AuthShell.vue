<script setup lang="ts">
import { Promotion, Search, Tickets } from '@element-plus/icons-vue'
import BrandLogo from '@/components/common/BrandLogo.vue'

withDefaults(
  defineProps<{
    title: string
    subtitle?: string
    /** 品牌侧标语 */
    tagline?: string
  }>(),
  {
    subtitle: '',
    tagline: '一次搜索，直飞 · 中转 · 临近三种方案尽在眼前',
  },
)

const features = [
  { icon: Search, text: '智能比价，快速锁定低价航班' },
  { icon: Tickets, text: '一站式预订、改签与退票' },
  { icon: Promotion, text: '中转衔接与临近机场智能推荐' },
]
</script>

<template>
  <div class="auth-shell" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 450 } }">
    <aside class="brand-side">
      <div class="brand-decor">
        <svg class="brand-plane" viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2A1.5 1.5 0 0 0 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1l3.5 1v-1.5L13 19v-5.5z"
          />
        </svg>
      </div>
      <BrandLogo :size="40" inverse />
      <p class="tagline">{{ tagline }}</p>
      <ul class="features">
        <li v-for="(item, index) in features" :key="index">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.text }}</span>
        </li>
      </ul>
    </aside>

    <section class="form-side">
      <header class="form-head">
        <h1>{{ title }}</h1>
        <p v-if="subtitle">{{ subtitle }}</p>
      </header>
      <slot />
    </section>
  </div>
</template>

<style scoped lang="scss">
.auth-shell {
  display: grid;
  grid-template-columns: 1fr 1fr;
  width: min(860px, 100%);
  background: var(--fa-surface);
  border-radius: var(--fa-radius-xl);
  box-shadow: var(--fa-shadow-3);
  overflow: hidden;
}

.brand-side {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 44px 38px;
  color: #fff;
  background: var(--fa-grad-brand-deep);
  overflow: hidden;
}

.brand-decor {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.brand-plane {
  position: absolute;
  top: -10px;
  right: -20px;
  width: 160px;
  height: 160px;
  color: rgba(255, 255, 255, 0.12);
  transform: rotate(28deg);
  animation: fa-float 7s ease-in-out infinite;
}

.tagline {
  margin: 6px 0 0;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.6;
  opacity: 0.95;
}

.features {
  display: grid;
  gap: 14px;
  margin: auto 0 0;
  padding: 0;
  list-style: none;
}

.features li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  opacity: 0.92;
}

.features .el-icon {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  font-size: 15px;
}

.form-side {
  padding: 44px 40px;
}

.form-head {
  margin-bottom: 24px;
}

.form-head h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.01em;
}

.form-head p {
  margin: 6px 0 0;
  color: var(--fa-text-tertiary);
  font-size: 14px;
}

@media (max-width: 720px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }

  .brand-side {
    display: none;
  }
}
</style>
