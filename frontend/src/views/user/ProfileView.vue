<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { userApi } from '@/api/user'
import EmptyState from '@/components/common/EmptyState.vue'
import type { Passenger, UserProfile } from '@/types/user'

const profile = ref<UserProfile | null>(null)
const passengers = ref<Passenger[]>([])

onMounted(async () => {
  try {
    profile.value = await userApi.getProfile()
    passengers.value = await userApi.listPassengers()
  } catch {
    profile.value = null
  }
})
</script>

<template>
  <div class="page-shell profile-page">
    <section class="page-section">
      <h1 class="page-title">个人信息</h1>
      <el-descriptions v-if="profile" :column="3" border>
        <el-descriptions-item label="用户 ID">{{ profile.user_id }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ profile.name }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ profile.phone }}</el-descriptions-item>
      </el-descriptions>
      <EmptyState v-else title="暂无个人信息" description="登录后可查看和维护个人资料。" />
    </section>

    <section class="page-section">
      <h2>常用乘机人</h2>
      <el-table :data="passengers" border>
        <el-table-column prop="id_no" label="证件号" min-width="210" />
        <el-table-column prop="real_name" label="姓名" width="140" />
        <el-table-column prop="birth_date" label="出生日期" width="160" />
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.profile-page {
  display: grid;
  gap: 16px;
}

h2 {
  margin: 0 0 12px;
  font-size: 16px;
}
</style>
