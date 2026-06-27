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
  ElMessage.success('登录成功')
  router.push(String(route.query.redirect || '/'))
}
</script>

<template>
  <AuthShell title="欢迎回来" subtitle="登录 FudanAir，继续你的旅程">
    <el-form :model="form" label-position="top" class="auth-form" @submit.prevent>
      <el-form-item label="手机号">
        <el-input v-model="form.phone" size="large" :prefix-icon="Iphone" autocomplete="username" placeholder="请输入手机号" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input
          v-model="form.password"
          size="large"
          type="password"
          :prefix-icon="Lock"
          autocomplete="current-password"
          show-password
          placeholder="请输入密码"
          @keyup.enter="submit"
        />
      </el-form-item>
      <el-button type="primary" size="large" class="full-button" @click="submit">登录</el-button>
    </el-form>
    <div class="auth-links">
      <RouterLink to="/register">注册新账号</RouterLink>
      <RouterLink to="/admin/login">管理员入口</RouterLink>
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
