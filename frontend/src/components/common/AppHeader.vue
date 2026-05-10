<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeMenu = computed(() => {
  if (route.path.startsWith('/orders')) {
    return '/orders'
  }
  return route.path
})

async function logout() {
  await auth.logout()
  ElMessage.success('已退出登录')
  router.push('/')
}
</script>

<template>
  <header class="app-header">
    <RouterLink class="brand" to="/">
      <span class="brand-mark">FA</span>
      <span>FudanAir</span>
    </RouterLink>

    <el-menu :default-active="activeMenu" mode="horizontal" router class="nav-menu">
      <el-menu-item index="/">航班搜索</el-menu-item>
      <el-menu-item index="/orders">我的订单</el-menu-item>
      <el-menu-item index="/profile">个人中心</el-menu-item>
    </el-menu>

    <div class="header-actions">
      <template v-if="auth.isAuthenticated">
        <span class="user-name">{{ auth.displayName }}</span>
        <el-button size="small" @click="logout">退出</el-button>
      </template>
      <template v-else>
        <el-button size="small" text @click="router.push('/login')">登录</el-button>
        <el-button size="small" type="primary" @click="router.push('/register')">注册</el-button>
      </template>
    </div>
  </header>
</template>

<style scoped lang="scss">
.app-header {
  display: grid;
  grid-template-columns: 180px 1fr auto;
  align-items: center;
  height: var(--fa-header-height);
  padding: 0 24px;
  background: var(--fa-white);
  border-bottom: 1px solid var(--fa-border);
}

.brand {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  color: var(--fa-text);
  font-size: 18px;
  font-weight: 700;
}

.brand-mark {
  display: inline-grid;
  width: 30px;
  height: 30px;
  place-items: center;
  color: #fff;
  background: var(--fa-brand);
  border-radius: 4px;
  font-size: 13px;
}

.nav-menu {
  border-bottom: none;
}

.header-actions {
  display: inline-flex;
  gap: 8px;
  align-items: center;
}

.user-name {
  color: var(--fa-text-secondary);
  font-size: 14px;
}
</style>
