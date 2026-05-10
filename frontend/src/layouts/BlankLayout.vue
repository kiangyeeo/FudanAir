<template>
  <main class="blank-layout">
    <RouterView />
  </main>
</template>

<style scoped>
.blank-layout {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
  background: var(--fa-bg);
}
</style>
