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
  ElMessage.success('Account created. Please sign in')
  router.push('/login')
}
</script>

<template>
  <AuthShell title="Create Account" subtitle="Join FudanAir and start your next trip">
    <el-form :model="form" label-position="top" class="auth-form" @submit.prevent>
      <el-form-item label="Name">
        <el-input v-model="form.name" size="large" :prefix-icon="User" placeholder="Enter name" />
      </el-form-item>
      <el-form-item label="Phone">
        <el-input v-model="form.phone" size="large" :prefix-icon="Iphone" autocomplete="username" placeholder="Enter phone number" />
      </el-form-item>
      <el-form-item label="Password">
        <el-input
          v-model="form.password"
          size="large"
          type="password"
          :prefix-icon="Lock"
          autocomplete="new-password"
          show-password
          placeholder="Set a 6-32 character password"
          @keyup.enter="submit"
        />
      </el-form-item>
      <el-button type="primary" size="large" class="full-button" @click="submit">Register</el-button>
    </el-form>
    <RouterLink class="back-link" to="/login">Already have an account? Log in</RouterLink>
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
