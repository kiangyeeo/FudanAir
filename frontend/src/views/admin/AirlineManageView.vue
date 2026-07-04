<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
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
const airlineKeyword = ref('')

const dialogVisible = ref(false)
const mode = ref<'create' | 'edit'>('create')
const editingIata = ref('')
const formRef = ref<FormInstance>()
const form = reactive<AirlineForm>({
  iata_code: '',
  airline_name: '',
})

const filteredAirlines = computed<Airline[]>(() => {
  const keyword = airlineKeyword.value.trim().toUpperCase()
  if (!keyword) {
    return airlines.value
  }
  return airlines.value.filter(
    (airline) => airline.iata_code.includes(keyword) || airline.airline_name.toUpperCase().includes(keyword),
  )
})

const rules: FormRules<AirlineForm> = {
  iata_code: [
    { required: true, message: 'Enter airline IATA code', trigger: 'blur' },
    { min: 2, max: 2, message: 'Airline code must be 2 characters', trigger: 'blur' },
  ],
  airline_name: [
    { required: true, message: 'Enter airline name', trigger: 'blur' },
    { max: 128, message: 'Airline name cannot exceed 128 characters', trigger: 'blur' },
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
  editingIata.value = ''
  Object.assign(form, { iata_code: '', airline_name: '' })
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

function openEdit(row: Airline) {
  mode.value = 'edit'
  editingIata.value = row.iata_code
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
    ElMessage.success('Airline added')
  } else {
    await adminApi.updateAirline(editingIata.value, payload)
    ElMessage.success('Airline updated')
  }
  dialogVisible.value = false
  await loadAirlines()
}

async function deleteAirline(row: Airline) {
  try {
    await ElMessageBox.confirm(`Delete airline ${row.iata_code}?`, 'Delete Airline', { type: 'warning' })
    await adminApi.deleteAirline(row.iata_code)
    ElMessage.success('Airline deleted')
    await loadAirlines()
  } catch {
    // 取消删除或后端已提示错误。
  }
}
</script>

<template>
  <section class="page-section admin-crud-page">
    <div class="toolbar">
      <h1 class="page-title">Airlines</h1>
      <div class="toolbar-actions">
        <el-input
          v-model="airlineKeyword"
          clearable
          :prefix-icon="Search"
          placeholder="Search code or name"
          class="airline-search"
        />
        <el-button type="primary" :icon="Plus" @click="openCreate">Add</el-button>
        <el-button :icon="Refresh" @click="loadAirlines">Refresh</el-button>
      </div>
    </div>

    <el-table
      v-if="airlines.length || loading"
      v-loading="loading"
      :data="filteredAirlines"
      empty-text="No matching airlines"
      border
      row-key="iata_code"
    >
      <el-table-column prop="iata_code" label="Airline Code" width="120" />
      <el-table-column prop="airline_name" label="Airline Name" min-width="240" />
      <el-table-column label="Actions" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :icon="Edit" @click="openEdit(row)">Edit</el-button>
          <el-button link type="danger" :icon="Delete" @click="deleteAirline(row)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>
    <EmptyState v-else title="No Airlines" description="No airline data." />

    <el-dialog
      v-model="dialogVisible"
      :title="mode === 'create' ? 'Add Airline' : 'Edit Airline'"
      width="460px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="Airline Code" prop="iata_code">
          <el-input v-model="form.iata_code" maxlength="2" />
        </el-form-item>
        <el-form-item label="Airline Name" prop="airline_name">
          <el-input v-model="form.airline_name" maxlength="128" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="submit">Save</el-button>
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

.airline-search {
  width: 220px;
}
</style>
