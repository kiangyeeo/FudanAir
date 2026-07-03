<script setup lang="ts">
import { reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Iphone, Lock } from '@element-plus/icons-vue'
import AuthShell from '@/components/common/AuthShell.vue'
import { useAuthStore } from '@/stores/auth'
import type { LoginRequest } from '@/types/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const form = reactive<LoginRequest>({ phone: '', password: '' })

async function submit() {
  await auth.login(form)
  ElMessage.success('Signed in')
  router.push(String(route.query.redirect || '/'))
}
</script>

<template>
  <AuthShell title="Welcome Back" subtitle="Sign in to FudanAir and continue your trip">
    <el-form :model="form" label-position="top" class="auth-form" @submit.prevent>
      <el-form-item label="Phone">
        <el-input v-model="form.phone" size="large" :prefix-icon="Iphone" autocomplete="username" placeholder="Enter phone number" />
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
      <el-button type="primary" size="large" class="full-button" @click="submit">Log In</el-button>
    </el-form>
    <div class="auth-links">
      <RouterLink to="/register">Create Account</RouterLink>
      <RouterLink to="/admin/login">Admin Portal</RouterLink>
    </div>
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

.auth-links {
  display: flex;
  justify-content: space-between;
  margin-top: 18px;
  color: var(--fa-brand);
  font-size: 14px;
}

.auth-links a {
  transition: opacity var(--fa-dur-fast) var(--fa-ease);
}

.auth-links a:hover {
  opacity: 0.7;
}
</style>
