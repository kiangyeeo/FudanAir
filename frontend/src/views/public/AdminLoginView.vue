<script setup lang="ts">
import { reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, UserFilled } from '@element-plus/icons-vue'
import AuthShell from '@/components/common/AuthShell.vue'
import { useAuthStore } from '@/stores/auth'
import type { AdminLoginRequest } from '@/types/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const form = reactive<AdminLoginRequest>({ admin_id: '', password: '' })

async function submit() {
  await auth.adminLogin(form)
  ElMessage.success('Admin signed in')
  router.push(String(route.query.redirect || '/admin'))
}
</script>

<template>
  <AuthShell title="Admin Login" subtitle="Access the FudanAir operations console">
    <el-form :model="form" label-position="top" class="auth-form" @submit.prevent>
      <el-form-item label="Admin ID">
        <el-input v-model="form.admin_id" size="large" :prefix-icon="UserFilled" autocomplete="username" placeholder="Enter admin ID" />
      </el-form-item>
      <el-form-item label="Password">
        <el-input
          v-model="form.password"
          size="large"
          type="password"
          :prefix-icon="Lock"
          autocomplete="current-password"
          show-password
          placeholder="Enter password"
          @keyup.enter="submit"
        />
      </el-form-item>
      <el-button type="primary" size="large" class="full-button" @click="submit">Log In to Admin</el-button>
    </el-form>
    <RouterLink class="back-link" to="/login">Back to User Login</RouterLink>
  </AuthShell>
</template>

<style scoped lang="scss">
.auth-form {
  display: grid;
  gap: 6px;
}

.full-button {
  width: 100%;
  margin-top: 8px;
}

.back-link {
  display: inline-block;
  margin-top: 18px;
  color: var(--fa-brand);
  font-size: 14px;
  transition: opacity var(--fa-dur-fast) var(--fa-ease);
}

.back-link:hover {
  opacity: 0.7;
}
</style>
