<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Iphone, Lock, User } from '@element-plus/icons-vue'
import AuthShell from '@/components/common/AuthShell.vue'
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
  <AuthShell title="创建账号" subtitle="加入 FudanAir，开启说走就走的旅程">
    <el-form :model="form" label-position="top" class="auth-form" @submit.prevent>
      <el-form-item label="姓名">
        <el-input v-model="form.name" size="large" :prefix-icon="User" placeholder="请输入姓名" />
      </el-form-item>
      <el-form-item label="手机号">
        <el-input v-model="form.phone" size="large" :prefix-icon="Iphone" autocomplete="username" placeholder="请输入手机号" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input
          v-model="form.password"
          size="large"
          type="password"
          :prefix-icon="Lock"
          autocomplete="new-password"
          show-password
          placeholder="设置 6-32 位密码"
          @keyup.enter="submit"
        />
      </el-form-item>
      <el-button type="primary" size="large" class="full-button" @click="submit">注册</el-button>
    </el-form>
    <RouterLink class="back-link" to="/login">已有账号，去登录</RouterLink>
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
