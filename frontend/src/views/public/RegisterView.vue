<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import type { RegisterRequest } from '@/types/auth'

const router = useRouter()
const auth = useAuthStore()
const form = reactive<RegisterRequest>({ phone: '', password: '', name: '' })

async function submit() {
  await auth.register(form)
  ElMessage.success('注册成功，请登录')
  router.push('/login')
}
</script>

<template>
  <section class="auth-panel">
    <h1>用户注册</h1>
    <el-form :model="form" label-position="top">
      <el-form-item label="姓名">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="手机号">
        <el-input v-model="form.phone" autocomplete="username" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" autocomplete="new-password" show-password />
      </el-form-item>
      <el-button type="primary" class="full-button" @click="submit">注册</el-button>
    </el-form>
    <RouterLink class="back-link" to="/login">已有账号，去登录</RouterLink>
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

:deep(.el-input__wrapper) {
  min-height: 48px;
  padding: 0 16px;
  border: 1px solid #d5d8df;
  border-radius: 2px;
  background: var(--fa-white);
  box-shadow: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: var(--fa-brand);
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12);
}

.full-button {
  width: 100%;
}

.back-link {
  display: inline-block;
  margin-top: 14px;
  color: var(--fa-brand);
  font-size: 14px;
}
</style>
