<script setup lang="ts">
import { reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import type { AdminLoginRequest } from '@/types/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const form = reactive<AdminLoginRequest>({ admin_id: '', password: '' })

async function submit() {
  await auth.adminLogin(form)
  ElMessage.success('管理员登录成功')
  router.push(String(route.query.redirect || '/admin'))
}
</script>

<template>
  <section class="auth-panel">
    <h1>管理员登录</h1>
    <el-form :model="form" label-position="top">
      <el-form-item label="管理员编号">
        <el-input v-model="form.admin_id" autocomplete="username" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" autocomplete="current-password" show-password />
      </el-form-item>
      <el-button type="primary" class="full-button" @click="submit">登录管理端</el-button>
    </el-form>
    <RouterLink class="back-link" to="/login">返回用户登录</RouterLink>
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

.back-link {
  display: inline-block;
  margin-top: 14px;
  color: var(--fa-brand);
  font-size: 14px;
}
</style>
