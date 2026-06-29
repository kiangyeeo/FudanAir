<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import EmptyState from '@/components/common/EmptyState.vue'
import { adminApi } from '@/api/admin'
import { flightApi } from '@/api/flight'
import type { AircraftType } from '@/types/flight'

interface AircraftForm {
  model: string
  economy_seats: number
  first_seats: number
}

const loading = ref(false)
const aircraftTypes = ref<AircraftType[]>([])
const aircraftKeyword = ref('')

const dialogVisible = ref(false)
const mode = ref<'create' | 'edit'>('create')
const editingModel = ref('')
const formRef = ref<FormInstance>()
const form = reactive<AircraftForm>({
  model: '',
  economy_seats: 0,
  first_seats: 0,
})

const filteredAircraftTypes = computed<AircraftType[]>(() => {
  const keyword = aircraftKeyword.value.trim().toUpperCase()
  if (!keyword) {
    return aircraftTypes.value
  }
  return aircraftTypes.value.filter((aircraftType) => aircraftType.model.toUpperCase().includes(keyword))
})

const validateSeatTotal = (_rule: unknown, _value: unknown, callback: (error?: Error) => void) => {
  if (form.economy_seats + form.first_seats <= 0) {
    callback(new Error('座位总数必须大于0'))
    return
  }
  callback()
}

const rules: FormRules<AircraftForm> = {
  model: [
    { required: true, message: '请输入机型', trigger: 'blur' },
    { max: 32, message: '机型不能超过32个字符', trigger: 'blur' },
  ],
  economy_seats: [
    { required: true, message: '请输入经济舱座位数', trigger: 'change' },
    { validator: validateSeatTotal, trigger: 'change' },
  ],
  first_seats: [
    { required: true, message: '请输入头等舱座位数', trigger: 'change' },
    { validator: validateSeatTotal, trigger: 'change' },
  ],
}

onMounted(loadAircraftTypes)

async function loadAircraftTypes() {
  loading.value = true
  try {
    aircraftTypes.value = await flightApi.listAircraftTypes()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  mode.value = 'create'
  editingModel.value = ''
  Object.assign(form, {
    model: '',
    economy_seats: 0,
    first_seats: 0,
  })
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

function openEdit(row: AircraftType) {
  mode.value = 'edit'
  editingModel.value = row.model
  Object.assign(form, row)
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

async function submit() {
  await formRef.value?.validate()
  const payload = {
    model: form.model.trim().toUpperCase(),
    economy_seats: form.economy_seats,
    first_seats: form.first_seats,
  }
  if (mode.value === 'create') {
    await adminApi.createAircraftType(payload)
    ElMessage.success('机型已新增')
  } else {
    await adminApi.updateAircraftType(editingModel.value, payload)
    ElMessage.success('机型已更新')
  }
  dialogVisible.value = false
  await loadAircraftTypes()
}

async function deleteAircraftType(row: AircraftType) {
  try {
    await ElMessageBox.confirm(`确认删除机型 ${row.model}？`, '删除机型', { type: 'warning' })
    await adminApi.deleteAircraftType(row.model)
    ElMessage.success('机型已删除')
    await loadAircraftTypes()
  } catch {
    // 取消删除或后端已提示错误。
  }
}
</script>

<template>
  <section class="page-section admin-crud-page">
    <div class="toolbar">
      <h1 class="page-title">机型管理</h1>
      <div class="toolbar-actions">
        <el-input
          v-model="aircraftKeyword"
          clearable
          :prefix-icon="Search"
          placeholder="搜索机型"
          class="aircraft-search"
        />
        <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
        <el-button :icon="Refresh" @click="loadAircraftTypes">刷新</el-button>
      </div>
    </div>

    <el-table
      v-if="aircraftTypes.length || loading"
      v-loading="loading"
      :data="filteredAircraftTypes"
      class="aircraft-table"
      empty-text="未找到匹配机型"
      border
      row-key="model"
    >
      <el-table-column prop="model" label="机型" min-width="180" />
      <el-table-column prop="economy_seats" label="经济舱座位" min-width="180" />
      <el-table-column prop="first_seats" label="头等舱座位" min-width="180" />
      <el-table-column label="总座位" min-width="160">
        <template #default="{ row }">{{ row.economy_seats + row.first_seats }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="180" align="center">
        <template #default="{ row }">
          <el-button link type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" :icon="Delete" @click="deleteAircraftType(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <EmptyState v-else title="暂无机型" description="机型数据为空。" />

    <el-dialog
      v-model="dialogVisible"
      :title="mode === 'create' ? '新增机型' : '编辑机型'"
      width="460px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="机型" prop="model">
          <el-input v-model="form.model" maxlength="32" />
        </el-form-item>
        <el-form-item label="经济舱座位" prop="economy_seats">
          <el-input-number v-model="form.economy_seats" :min="0" :max="999" :step="1" :precision="0" class="full-width" />
        </el-form-item>
        <el-form-item label="头等舱座位" prop="first_seats">
          <el-input-number v-model="form.first_seats" :min="0" :max="999" :step="1" :precision="0" class="full-width" />
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

.aircraft-search {
  width: 220px;
}

.aircraft-table {
  width: 100%;
}

.full-width {
  width: 100%;
}
</style>
