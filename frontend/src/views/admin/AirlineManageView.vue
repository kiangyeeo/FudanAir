<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Delete, Edit, Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import EmptyState from '@/components/common/EmptyState.vue'
import { adminApi } from '@/api/admin'
import { flightApi } from '@/api/flight'
import type { Airline } from '@/types/flight'

interface AirlineForm {
  iata_code: string
  airline_name: string
}

const loading = ref(false)
const airlines = ref<Airline[]>([])

const dialogVisible = ref(false)
const mode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()
const form = reactive<AirlineForm>({
  iata_code: '',
  airline_name: '',
})

const rules: FormRules<AirlineForm> = {
  iata_code: [
    { required: true, message: '请输入航司二字码', trigger: 'blur' },
    { min: 2, max: 2, message: '航司代码必须为2位', trigger: 'blur' },
  ],
  airline_name: [
    { required: true, message: '请输入航司名称', trigger: 'blur' },
    { max: 128, message: '航司名称不能超过128个字符', trigger: 'blur' },
  ],
}

onMounted(loadAirlines)

async function loadAirlines() {
  loading.value = true
  try {
    airlines.value = await flightApi.listAirlines()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  mode.value = 'create'
  Object.assign(form, { iata_code: '', airline_name: '' })
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

function openEdit(row: Airline) {
  mode.value = 'edit'
  Object.assign(form, row)
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

async function submit() {
  await formRef.value?.validate()
  const payload = {
    iata_code: form.iata_code.trim().toUpperCase(),
    airline_name: form.airline_name.trim(),
  }
  if (mode.value === 'create') {
    await adminApi.createAirline(payload)
    ElMessage.success('航司已新增')
  } else {
    await adminApi.updateAirline(payload.iata_code, { airline_name: payload.airline_name })
    ElMessage.success('航司已更新')
  }
  dialogVisible.value = false
  await loadAirlines()
}

async function deleteAirline(row: Airline) {
  try {
    await ElMessageBox.confirm(`确认删除航司 ${row.iata_code}？`, '删除航司', { type: 'warning' })
    await adminApi.deleteAirline(row.iata_code)
    ElMessage.success('航司已删除')
    await loadAirlines()
  } catch {
    // 取消删除或后端已提示错误。
  }
}
</script>

<template>
  <section class="page-section admin-crud-page">
    <div class="toolbar">
      <h1 class="page-title">航司管理</h1>
      <div class="toolbar-actions">
        <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
        <el-button :icon="Refresh" @click="loadAirlines">刷新</el-button>
      </div>
    </div>

    <el-table
      v-if="airlines.length || loading"
      v-loading="loading"
      :data="airlines"
      border
      row-key="iata_code"
    >
      <el-table-column prop="iata_code" label="航司代码" width="120" />
      <el-table-column prop="airline_name" label="航司名称" min-width="240" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" :icon="Delete" @click="deleteAirline(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <EmptyState v-else title="暂无航司" description="航司数据为空。" />

    <el-dialog
      v-model="dialogVisible"
      :title="mode === 'create' ? '新增航司' : '编辑航司'"
      width="460px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="航司二字码" prop="iata_code">
          <el-input v-model="form.iata_code" maxlength="2" :disabled="mode === 'edit'" />
        </el-form-item>
        <el-form-item label="航司名称" prop="airline_name">
          <el-input v-model="form.airline_name" maxlength="128" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.admin-crud-page {
  display: grid;
  gap: 12px;
}

.toolbar {
  justify-content: space-between;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
