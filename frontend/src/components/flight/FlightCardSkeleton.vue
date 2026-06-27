<script setup lang="ts">
withDefaults(defineProps<{ count?: number }>(), { count: 4 })
</script>

<template>
  <div class="skeleton-list">
    <div v-for="i in count" :key="i" class="skeleton-card">
      <span class="fa-skeleton logo" />
      <span class="fa-skeleton time" />
      <div class="mid">
        <span class="fa-skeleton bar w60" />
        <span class="fa-skeleton bar w40" />
      </div>
      <span class="fa-skeleton time" />
      <div class="price">
        <span class="fa-skeleton bar w80" />
        <span class="fa-skeleton btn" />
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.skeleton-list {
  display: grid;
  gap: 12px;
}

.skeleton-card {
  display: grid;
  grid-template-columns: 44px 80px 1fr 80px 150px;
  gap: 16px;
  align-items: center;
  padding: 18px;
  background: var(--fa-surface);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
}

.logo {
  width: 40px;
  height: 40px;
  border-radius: 10px;
}

.time {
  width: 64px;
  height: 26px;
}

.mid {
  display: grid;
  gap: 8px;
  justify-items: center;
}

.price {
  display: grid;
  gap: 8px;
  justify-items: end;
}

.bar {
  height: 14px;
}

.w40 {
  width: 40%;
}

.w60 {
  width: 60%;
}

.w80 {
  width: 90px;
}

.btn {
  width: 84px;
  height: 32px;
  border-radius: var(--fa-radius-pill);
}

@media (max-width: 760px) {
  .skeleton-card {
    grid-template-columns: 44px 1fr;
  }

  .mid,
  .price {
    grid-column: 1 / -1;
    justify-items: start;
  }
}
</style>
