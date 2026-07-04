<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import EmptyState from '@/components/common/EmptyState.vue'
import { adminApi } from '@/api/admin'
import { flightApi } from '@/api/flight'
import type { Airport } from '@/types/flight'

interface AirportForm {
  iata_code: string
  airport_name: string
  city_name: string
}

const loading = ref(false)
const airports = ref<Airport[]>([])
const cities = ref<string[]>([])
const cityFilter = ref('')

const dialogVisible = ref(false)
const mode = ref<'create' | 'edit'>('create')
const editingIata = ref('')
const formRef = ref<FormInstance>()
const form = reactive<AirportForm>({
  iata_code: '',
  airport_name: '',
  city_name: '',
})

const rules: FormRules<AirportForm> = {
  iata_code: [
    { required: true, message: 'Enter airport IATA code', trigger: 'blur' },
    { min: 3, max: 3, message: 'Airport code must be 3 characters', trigger: 'blur' },
  ],
  airport_name: [
    { required: true, message: 'Enter airport name', trigger: 'blur' },
    { max: 128, message: 'Airport name cannot exceed 128 characters', trigger: 'blur' },
  ],
  city_name: [{ required: true, message: 'Select city', trigger: 'change' }],
}

onMounted(async () => {
  await Promise.all([loadCities(), loadAirports()])
})

async function loadCities() {
  cities.value = await flightApi.listCities()
}

async function loadAirports() {
  loading.value = true
  try {
    airports.value = await flightApi.listAirports(cityFilter.value ? { city: cityFilter.value } : {})
  } finally {
    loading.value = false
  }
}

function openCreate() {
  mode.value = 'create'
  editingIata.value = ''
  Object.assign(form, {
    iata_code: '',
    airport_name: '',
    city_name: '',
  })
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

function openEdit(row: Airport) {
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
    airport_name: form.airport_name.trim(),
    city_name: form.city_name,
  }
  if (mode.value === 'create') {
    await adminApi.createAirport(payload)
    ElMessage.success('Airport added')
  } else {
    await adminApi.updateAirport(editingIata.value, payload)
    ElMessage.success('Airport updated')
  }
  dialogVisible.value = false
  await loadAirports()
}

async function deleteAirport(row: Airport) {
  try {
    await ElMessageBox.confirm(`Delete airport ${row.iata_code}?`, 'Delete Airport', { type: 'warning' })
    await adminApi.deleteAirport(row.iata_code)
    ElMessage.success('Airport deleted')
    await loadAirports()
  } catch {
    // 取消删除或后端已提示错误。
  }
}
</script>

<template>
  <section class="page-section admin-crud-page">
    <div class="toolbar">
      <h1 class="page-title">Airports</h1>
      <div class="toolbar-actions">
        <el-select v-model="cityFilter" clearable filterable placeholder="City" class="filter-select">
          <el-option v-for="city in cities" :key="city" :label="city" :value="city" />
        </el-select>
        <el-button :icon="Search" @click="loadAirports">Filter</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">Add</el-button>
        <el-button :icon="Refresh" @click="loadAirports">Refresh</el-button>
      </div>
    </div>

    <el-table
      v-if="airports.length || loading"
      v-loading="loading"
      :data="airports"
      border
      row-key="iata_code"
    >
      <el-table-column prop="iata_code" label="IATA" width="100" />
      <el-table-column prop="airport_name" label="Airport Name" min-width="240" />
      <el-table-column prop="city_name" label="City" width="140" />
      <el-table-column label="Actions" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :icon="Edit" @click="openEdit(row)">Edit</el-button>
          <el-button link type="danger" :icon="Delete" @click="deleteAirport(row)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>
    <EmptyState v-else title="No Airports" description="No airport data." />

    <el-dialog
      v-model="dialogVisible"
      :title="mode === 'create' ? 'Add Airport' : 'Edit Airport'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="IATA Code" prop="iata_code">
          <el-input v-model="form.iata_code" maxlength="3" />
        </el-form-item>
        <el-form-item label="Airport Name" prop="airport_name">
          <el-input v-model="form.airport_name" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="City" prop="city_name">
          <el-select v-model="form.city_name" filterable class="full-width">
            <el-option v-for="city in cities" :key="city" :label="city" :value="city" />
          </el-select>
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

.filter-select {
  width: 180px;
}

.full-width {
  width: 100%;
}
</style>
