<script setup lang="ts">
import { reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
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
  <section class="auth-panel">
    <h1>用户登录</h1>
    <el-form :model="form" label-position="top">
      <el-form-item label="手机号">
        <el-input v-model="form.phone" autocomplete="username" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" autocomplete="current-password" show-password />
      </el-form-item>
      <el-button type="primary" class="full-button" @click="submit">登录</el-button>
    </el-form>
    <div class="auth-links">
      <RouterLink to="/register">注册用户账号</RouterLink>
      <RouterLink to="/admin/login">管理员入口</RouterLink>
    </div>
  </section>
</template>

<style scoped lang="scss">
.auth-panel {
  width: min(380px, 100%);
  padding: 22px;
  background: var(--fa-white);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
}

h1 {
  margin: 0 0 18px;
  font-size: 22px;
}

.full-button {
  width: 100%;
}

.auth-links {
  display: flex;
  justify-content: space-between;
  margin-top: 14px;
  color: var(--fa-brand);
  font-size: 14px;
}
</style>
