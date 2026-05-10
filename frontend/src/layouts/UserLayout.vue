<script setup lang="ts">
import AppFooter from '@/components/common/AppFooter.vue'
import AppHeader from '@/components/common/AppHeader.vue'
</script>

<template>
  <div class="user-layout">
    <AppHeader />
    <main class="user-main">
      <RouterView />
    </main>
    <AppFooter />
  </div>
</template>

<style scoped>
.user-layout {
  min-height: 100vh;
}

.user-main {
  padding: 20px 0 0;
}
</style>
