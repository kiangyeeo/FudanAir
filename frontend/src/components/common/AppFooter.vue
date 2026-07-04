<script setup lang="ts">
import BrandLogo from '@/components/common/BrandLogo.vue'

const year = new Date().getFullYear()
</script>

<template>
  <footer class="app-footer">
    <div class="footer-inner">
      <BrandLogo :size="46" text="FudanAir Airline Ticketing System" />
      <div class="footer-meta">
        <span>© {{ year }} FudanAir · Database Systems Course Project</span>
      </div>
    </div>
  </footer>
</template>

<style scoped lang="scss">
.app-footer {
  margin-top: 40px;
  border-top: 1px solid var(--fa-border);
  background: var(--fa-surface);
}

.footer-inner {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 24px 0;
}

.footer-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  color: var(--fa-text-tertiary);
  font-size: 13px;
}

@media (max-width: 600px) {
  .footer-meta {
    align-items: flex-start;
  }
}
</style>
