<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { refundApi } from '@/api/refund'
import type { ChangeRequest } from '@/types/refund'

const loading = ref(false)
const form = reactive<ChangeRequest>({
  ticket_no: '',
  new_instance_id: '',
  new_cabin_class: '经济舱',
  new_fare_type: '标准',
})

async function submit() {
  loading.value = true
  try {
    await refundApi.change(form)
    ElMessage.success('改签申请已提交')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-shell">
    <section class="page-section change-panel">
      <h1 class="page-title">改签</h1>
      <el-form :model="form" label-position="top">
        <el-form-item label="原客票号">
          <el-input v-model="form.ticket_no" />
        </el-form-item>
        <el-form-item label="新航班实例">
          <el-input v-model="form.new_instance_id" />
        </el-form-item>
        <el-form-item label="新舱位">
          <el-select v-model="form.new_cabin_class">
            <el-option label="经济舱" value="经济舱" />
            <el-option label="头等舱" value="头等舱" />
          </el-select>
        </el-form-item>
        <el-form-item label="票价类型">
          <el-select v-model="form.new_fare_type">
            <el-option label="标准" value="标准" />
            <el-option label="特价" value="特价" />
          </el-select>
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="submit">提交改签</el-button>
      </el-form>
    </section>
  </div>
</template>

<style scoped>
.change-panel {
  max-width: 560px;
}
</style>
