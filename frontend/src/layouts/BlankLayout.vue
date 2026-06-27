<template>
  <main class="blank-layout">
    <RouterView v-slot="{ Component }">
      <Transition name="fade-slide" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
  </main>
</template>

<style scoped>
.blank-layout {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(1100px 520px at 18% -8%, rgba(54, 198, 255, 0.16), transparent 60%),
    radial-gradient(900px 460px at 110% 110%, rgba(22, 119, 255, 0.14), transparent 55%),
    var(--fa-bg);
}
</style>
