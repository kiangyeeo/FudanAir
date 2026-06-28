<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    subtitle?: string
  }>(),
  {
    subtitle: '',
  },
)
</script>

<template>
  <div class="auth-shell" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 450 } }">
    <aside class="brand-side">
      <div class="brand-medallion">
        <img src="/images/brand-emblem.png" alt="FudanAir 航空票务数据库管理系统" />
      </div>
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
  align-items: center;
  justify-content: center;
  padding: 44px 38px;
  color: #fff;
  background: var(--fa-grad-brand-deep);
  overflow: hidden;
}

.brand-medallion {
  display: grid;
  place-items: center;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 0 0 8px rgba(255, 255, 255, 0.12), 0 18px 40px rgba(0, 0, 0, 0.3);
  animation: fa-float 6s ease-in-out infinite;
}

.brand-medallion img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
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
