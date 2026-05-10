<template>
  <footer class="app-footer">
    <span>FudanAir 航空票务管理数据库系统</span>
    <span>本地开发环境</span>
  </footer>
</template>

<style scoped lang="scss">
.app-footer {
  display: flex;
  justify-content: space-between;
  width: min(1180px, calc(100% - 32px));
  margin: 24px auto 0;
  padding: 16px 0 24px;
  color: var(--fa-text-secondary);
  font-size: 13px;
  border-top: 1px solid var(--fa-border);
}
</style>
