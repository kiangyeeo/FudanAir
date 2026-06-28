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
  ElMessage.success('管理员登录成功')
  router.push(String(route.query.redirect || '/admin'))
}
</script>

<template>
  <AuthShell title="管理员登录" subtitle="进入 FudanAir 运营管理后台">
    <el-form :model="form" label-position="top" class="auth-form" @submit.prevent>
      <el-form-item label="管理员编号">
        <el-input v-model="form.admin_id" size="large" :prefix-icon="UserFilled" autocomplete="username" placeholder="请输入管理员编号" />
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
      <el-button type="primary" size="large" class="full-button" @click="submit">登录管理端</el-button>
    </el-form>
    <RouterLink class="back-link" to="/login">返回用户登录</RouterLink>
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
