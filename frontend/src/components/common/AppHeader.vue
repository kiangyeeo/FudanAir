<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, Tickets, User, SwitchButton } from '@element-plus/icons-vue'
import BrandLogo from '@/components/common/BrandLogo.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const scrolled = ref(false)

const activeMenu = computed(() => {
  if (route.path.startsWith('/orders')) {
    return '/orders'
  }
  return route.path
})

const avatarText = computed(() => (auth.displayName || 'U').trim().charAt(0).toUpperCase())

function onScroll() {
  scrolled.value = window.scrollY > 4
}

async function handleCommand(command: string) {
  if (command === 'logout') {
    await auth.logout()
    ElMessage.success('已退出登录')
    router.push('/')
    return
  }
  router.push(command)
}

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
  onScroll()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
})
</script>

<template>
  <header class="app-header" :class="{ scrolled }">
    <RouterLink class="brand" to="/">
      <BrandLogo :size="72" />
    </RouterLink>

    <el-menu :default-active="activeMenu" mode="horizontal" router class="nav-menu" :ellipsis="false">
      <el-menu-item index="/">航班搜索</el-menu-item>
      <el-menu-item index="/trips">我的机票</el-menu-item>
      <el-menu-item index="/orders">我的订单</el-menu-item>
      <el-menu-item index="/profile">个人中心</el-menu-item>
    </el-menu>

    <div class="header-actions">
      <template v-if="auth.isAuthenticated">
        <el-dropdown trigger="click" @command="handleCommand">
          <span class="user-trigger">
            <span class="avatar">{{ avatarText }}</span>
            <span class="user-name">{{ auth.displayName }}</span>
            <el-icon class="caret"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="/profile" :icon="User">个人中心</el-dropdown-item>
              <el-dropdown-item command="/orders" :icon="Tickets">我的订单</el-dropdown-item>
              <el-dropdown-item command="logout" :icon="SwitchButton" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
      <template v-else>
        <el-button text @click="router.push('/login')">登录</el-button>
        <el-button type="primary" round @click="router.push('/register')">注册</el-button>
      </template>
    </div>
  </header>
</template>

<style scoped lang="scss">
.app-header {
  position: sticky;
  top: 0;
  z-index: var(--fa-z-header);
  display: grid;
  grid-template-columns: 220px 1fr auto;
  align-items: center;
  height: var(--fa-header-height);
  padding: 0 40px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid transparent;
  transition: box-shadow var(--fa-dur-base) var(--fa-ease), border-color var(--fa-dur-base) var(--fa-ease);
}

.app-header.scrolled {
  border-bottom-color: var(--fa-border);
  box-shadow: var(--fa-shadow-1);
}

.brand {
  display: inline-flex;
  align-items: center;
}

/* 顶栏徽标不要描边/阴影 */
.brand :deep(.mark) {
  box-shadow: none;
}

.nav-menu {
  height: var(--fa-header-height);
  border-bottom: none;
  background: transparent;
}

.nav-menu :deep(.el-menu-item) {
  height: var(--fa-header-height);
  padding: 0 22px;
  font-size: 15px;
  font-weight: 500;
  line-height: var(--fa-header-height);
}

.nav-menu :deep(.el-menu-item.is-active) {
  font-weight: 600;
}

.header-actions {
  display: inline-flex;
  gap: 8px;
  align-items: center;
}

.user-trigger {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  padding: 5px 10px 5px 5px;
  border-radius: var(--fa-radius-pill);
  cursor: pointer;
  transition: background-color var(--fa-dur-fast) var(--fa-ease);
}

.user-trigger:hover {
  background: var(--fa-surface-2);
}

.avatar {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  color: #fff;
  background: var(--fa-grad-brand);
  font-size: 13px;
  font-weight: 700;
}

.user-name {
  color: var(--fa-text);
  font-size: 14px;
  font-weight: 500;
}

.caret {
  color: var(--fa-text-tertiary);
  font-size: 12px;
}

@media (max-width: 760px) {
  .app-header {
    grid-template-columns: auto 1fr auto;
    padding: 0 16px;
  }

  .user-name {
    display: none;
  }
}
</style>
