<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Odometer,
  MapLocation,
  Position,
  Promotion,
  Box,
  Calendar,
  Document,
  Money,
  Tickets,
  Fold,
  Expand,
  SwitchButton,
} from '@element-plus/icons-vue'
import BrandLogo from '@/components/common/BrandLogo.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collapsed = ref(false)

const menus = [
  { index: '/admin', label: 'Dashboard', icon: Odometer },
  { index: '/admin/cities', label: 'Cities', icon: MapLocation },
  { index: '/admin/airports', label: 'Airports', icon: Position },
  { index: '/admin/airlines', label: 'Airlines', icon: Promotion },
  { index: '/admin/aircraft', label: 'Aircraft Types', icon: Box },
  { index: '/admin/flights', label: 'Flights', icon: Calendar },
  { index: '/admin/instances', label: 'Flight Instances', icon: Document },
  { index: '/admin/prices', label: 'Pricing', icon: Money },
  { index: '/admin/orders', label: 'Orders', icon: Tickets },
]

const activeMenu = computed(() => route.path)
const title = computed(() => route.meta.title || 'Admin Console')

async function logout() {
  await auth.logout()
  ElMessage.success('Admin signed out')
  router.push('/admin/login')
}
</script>

<template>
  <el-container class="admin-layout">
    <el-aside :width="collapsed ? '68px' : '224px'" class="admin-aside">
      <RouterLink to="/admin" class="admin-brand">
        <BrandLogo :size="30" :show-text="!collapsed" text="FudanAir" inverse />
      </RouterLink>
      <el-menu :default-active="activeMenu" :collapse="collapsed" router class="admin-menu">
        <el-menu-item v-for="menu in menus" :key="menu.index" :index="menu.index">
          <el-icon><component :is="menu.icon" /></el-icon>
          <template #title>{{ menu.label }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <div class="header-left">
          <el-button text class="collapse-btn" @click="collapsed = !collapsed">
            <el-icon><component :is="collapsed ? Expand : Fold" /></el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>Admin</el-breadcrumb-item>
            <el-breadcrumb-item>{{ title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="admin-user">
          <span class="avatar">{{ (auth.displayName || 'A').charAt(0).toUpperCase() }}</span>
          <span class="name">{{ auth.displayName || 'Admin' }}</span>
          <el-button :icon="SwitchButton" text @click="logout">Sign Out</el-button>
        </div>
      </el-header>
      <el-main class="admin-main">
        <RouterView v-slot="{ Component, route: r }">
          <Transition name="fade-slide" mode="out-in">
            <component :is="Component" :key="r.path" />
          </Transition>
        </RouterView>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped lang="scss">
.admin-layout {
  min-height: 100vh;
}

.admin-aside {
  background: linear-gradient(180deg, #0b234f 0%, #0d2a5e 100%);
  transition: width var(--fa-dur-base) var(--fa-ease);
  overflow-x: hidden;
}

.admin-brand {
  display: flex;
  align-items: center;
  height: 60px;
  padding: 0 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.admin-menu {
  padding: 10px;
  background: transparent;
  border-right: none;
}

.admin-menu :deep(.el-menu-item) {
  height: 46px;
  margin: 4px 0;
  border-radius: var(--fa-radius);
  color: rgba(255, 255, 255, 0.78);
}

.admin-menu :deep(.el-menu-item .el-icon) {
  color: rgba(255, 255, 255, 0.6);
}

.admin-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background: var(--fa-grad-brand);
  color: #fff;
  box-shadow: 0 6px 16px rgba(22, 119, 255, 0.35);
}

.admin-menu :deep(.el-menu-item.is-active .el-icon) {
  color: #fff;
}

.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--fa-surface);
  border-bottom: 1px solid var(--fa-border);
  box-shadow: var(--fa-shadow-1);
}

.header-left {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.collapse-btn {
  font-size: 18px;
}

.admin-user {
  display: inline-flex;
  gap: 10px;
  align-items: center;
  color: var(--fa-text-secondary);
}

.admin-user .avatar {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  color: #fff;
  background: var(--fa-grad-brand);
  font-size: 13px;
  font-weight: 700;
}

.admin-user .name {
  font-size: 14px;
  font-weight: 500;
  color: var(--fa-text);
}

.admin-main {
  background: var(--fa-bg);
}
</style>
