<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { refundApi } from '@/api/refund'

const route = useRoute()
const loading = ref(false)
const form = reactive({ ticket_no: '' })

async function submit() {
  loading.value = true
  try {
    await refundApi.refund({ ticket_no: form.ticket_no })
    ElMessage.success('退票申请已提交')
  } finally {
    loading.value = false
  }
}

function queryText(key: string): string | null {
  const value = route.query[key]
  if (Array.isArray(value)) {
    return value[0] ?? null
  }
  return value ?? null
}

onMounted(() => {
  form.ticket_no = queryText('ticket_no') ?? ''
})
</script>

<template>
  <div class="page-shell">
    <section class="page-section refund-panel">
      <h1 class="page-title">退票</h1>
      <el-form :model="form" label-position="top">
        <el-form-item label="客票号">
          <el-input v-model="form.ticket_no" placeholder="输入需要退票的 ticket_no" />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="submit">提交退票</el-button>
      </el-form>
    </section>
  </div>
</template>

<style scoped>
.refund-panel {
  max-width: 520px;
}
</style>
