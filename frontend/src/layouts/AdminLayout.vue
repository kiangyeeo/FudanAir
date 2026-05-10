<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeMenu = computed(() => route.path)
const title = computed(() => route.meta.title || '管理后台')

async function logout() {
  await auth.logout()
  ElMessage.success('已退出管理员登录')
  router.push('/admin/login')
}
</script>

<template>
  <el-container class="admin-layout">
    <el-aside width="220px" class="admin-aside">
      <RouterLink to="/admin" class="admin-brand">
        <span class="brand-mark">FA</span>
        <span>FudanAir Admin</span>
      </RouterLink>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/admin">管理概览</el-menu-item>
        <el-menu-item index="/admin/cities">城市管理</el-menu-item>
        <el-menu-item index="/admin/airports">机场管理</el-menu-item>
        <el-menu-item index="/admin/airlines">航司管理</el-menu-item>
        <el-menu-item index="/admin/aircraft">机型管理</el-menu-item>
        <el-menu-item index="/admin/flights">航班管理</el-menu-item>
        <el-menu-item index="/admin/instances">实例管理</el-menu-item>
        <el-menu-item index="/admin/prices">票价管理</el-menu-item>
        <el-menu-item index="/admin/orders">订单查询</el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item>管理端</el-breadcrumb-item>
          <el-breadcrumb-item>{{ title }}</el-breadcrumb-item>
        </el-breadcrumb>
        <div class="admin-user">
          <span>{{ auth.displayName || '管理员' }}</span>
          <el-button size="small" @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main class="admin-main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped lang="scss">
.admin-layout {
  min-height: 100vh;
}

.admin-aside {
  background: var(--fa-white);
  border-right: 1px solid var(--fa-border);
}

.admin-brand {
  display: flex;
  gap: 8px;
  align-items: center;
  height: 56px;
  padding: 0 18px;
  font-weight: 700;
  border-bottom: 1px solid var(--fa-border);
}

.brand-mark {
  display: inline-grid;
  width: 28px;
  height: 28px;
  place-items: center;
  color: #fff;
  background: var(--fa-brand);
  border-radius: 4px;
  font-size: 12px;
}

.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--fa-white);
  border-bottom: 1px solid var(--fa-border);
}

.admin-user {
  display: inline-flex;
  gap: 10px;
  align-items: center;
  color: var(--fa-text-secondary);
}

.admin-main {
  background: var(--fa-bg);
}
</style>
