<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import EmptyState from '@/components/common/EmptyState.vue'
import { adminApi } from '@/api/admin'
import { flightApi } from '@/api/flight'
import type { Airport, NearAirport } from '@/types/flight'

interface CityRow {
  city_name: string
}

interface CityForm {
  city_name: string
}

interface NearForm {
  iata_code: string
  distance: number
}

const loading = ref(false)
const nearLoading = ref(false)
const cities = ref<string[]>([])
const airports = ref<Airport[]>([])
const nearAirports = ref<NearAirport[]>([])
const selectedCity = ref('')
const cityKeyword = ref('')

const cityRows = computed<CityRow[]>(() => cities.value.map((cityName) => ({ city_name: cityName })))
const filteredCityRows = computed<CityRow[]>(() => {
  const keyword = cityKeyword.value.trim()
  if (!keyword) {
    return cityRows.value
  }
  return cityRows.value.filter((row) => row.city_name.includes(keyword))
})

const cityDialogVisible = ref(false)
const cityMode = ref<'create' | 'edit'>('create')
const editingCity = ref('')
const cityFormRef = ref<FormInstance>()
const cityForm = reactive<CityForm>({ city_name: '' })
const cityRules: FormRules<CityForm> = {
  city_name: [
    { required: true, message: 'Enter city name', trigger: 'blur' },
    { max: 32, message: 'City name cannot exceed 32 characters', trigger: 'blur' },
  ],
}

const nearManageDialogVisible = ref(false)
const nearDialogVisible = ref(false)
const nearFormRef = ref<FormInstance>()
const nearForm = reactive<NearForm>({ iata_code: '', distance: 0 })
const nearRules: FormRules<NearForm> = {
  iata_code: [{ required: true, message: 'Select an airport', trigger: 'change' }],
  distance: [{ required: true, message: 'Enter distance', trigger: 'change' }],
}

onMounted(async () => {
  await Promise.all([loadCities(), loadAirports()])
})

async function loadCities() {
  loading.value = true
  try {
    cities.value = await flightApi.listCities()
    if (selectedCity.value && !cities.value.includes(selectedCity.value)) {
      selectedCity.value = ''
      nearAirports.value = []
      nearManageDialogVisible.value = false
    }
  } finally {
    loading.value = false
  }
}

async function loadAirports() {
  airports.value = await flightApi.listAirports()
}

async function loadNearAirports() {
  if (!selectedCity.value) {
    nearAirports.value = []
    return
  }
  nearLoading.value = true
  try {
    nearAirports.value = await flightApi.listNearAirports(selectedCity.value)
  } finally {
    nearLoading.value = false
  }
}

async function openNearAirportManage(row: CityRow) {
  selectedCity.value = row.city_name
  nearManageDialogVisible.value = true
  await loadNearAirports()
}

function openCreateCity() {
  cityMode.value = 'create'
  editingCity.value = ''
  cityForm.city_name = ''
  cityDialogVisible.value = true
  cityFormRef.value?.clearValidate()
}

function openEditCity(row: CityRow) {
  cityMode.value = 'edit'
  editingCity.value = row.city_name
  cityForm.city_name = row.city_name
  cityDialogVisible.value = true
  cityFormRef.value?.clearValidate()
}

async function submitCity() {
  await cityFormRef.value?.validate()
  const cityName = cityForm.city_name.trim()
  if (cityMode.value === 'create') {
    await adminApi.createCity({ city_name: cityName })
    ElMessage.success('City added')
  } else {
    await adminApi.updateCity(editingCity.value, { city_name: cityName })
    selectedCity.value = cityName
    ElMessage.success('City updated')
  }
  cityDialogVisible.value = false
  await loadCities()
}

async function deleteCity(row: CityRow) {
  try {
    await ElMessageBox.confirm(`Delete city ${row.city_name}?`, 'Delete City', { type: 'warning' })
    await adminApi.deleteCity(row.city_name)
    if (selectedCity.value === row.city_name) {
      selectedCity.value = ''
      nearAirports.value = []
      nearManageDialogVisible.value = false
    }
    ElMessage.success('City deleted')
    await loadCities()
  } catch {
    // 取消删除或后端已提示错误。
  }
}

function openCreateNearAirport() {
  if (!selectedCity.value) {
    return
  }
  nearForm.iata_code = ''
  nearForm.distance = 0
  nearDialogVisible.value = true
  nearFormRef.value?.clearValidate()
}

async function submitNearAirport() {
  await nearFormRef.value?.validate()
  await adminApi.createNearAirport(selectedCity.value, {
    iata_code: nearForm.iata_code.trim().toUpperCase(),
    distance: nearForm.distance,
  })
  nearDialogVisible.value = false
  ElMessage.success('Nearby airport added')
  await loadNearAirports()
}

async function deleteNearAirport(row: NearAirport) {
  try {
    await ElMessageBox.confirm(`Delete relation between ${selectedCity.value} and ${row.iata_code}?`, 'Delete Nearby Airport', { type: 'warning' })
    await adminApi.deleteNearAirport(selectedCity.value, row.iata_code)
    ElMessage.success('Nearby airport deleted')
    await loadNearAirports()
  } catch {
    // 取消删除或后端已提示错误。
  }
}
</script>

<template>
  <div class="admin-crud-page">
    <section class="page-section">
      <div class="toolbar">
        <h1 class="page-title">Cities</h1>
        <div class="toolbar-actions">
          <el-input
            v-model="cityKeyword"
            clearable
            :prefix-icon="Search"
            placeholder="Search city name"
            class="city-search"
          />
          <el-button type="primary" :icon="Plus" @click="openCreateCity">Add</el-button>
          <el-button :icon="Refresh" @click="loadCities">Refresh</el-button>
        </div>
      </div>

      <el-table
        v-if="cities.length || loading"
        v-loading="loading"
        :data="filteredCityRows"
        empty-text="No matching cities"
        border
        row-key="city_name"
        highlight-current-row
      >
        <el-table-column prop="city_name" label="City Name" min-width="180" />
        <el-table-column label="Actions" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Search" @click="openNearAirportManage(row)">Nearby Airports</el-button>
            <el-button link type="primary" :icon="Edit" @click="openEditCity(row)">Edit</el-button>
            <el-button link type="danger" :icon="Delete" @click="deleteCity(row)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else title="No Cities" description="No city data." />
    </section>

    <el-dialog
      v-model="nearManageDialogVisible"
      width="760px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template #header>
        <div class="near-dialog-title">
          <span>Nearby Airports</span>
          <el-tag v-if="selectedCity" type="info">{{ selectedCity }}</el-tag>
        </div>
      </template>

      <div class="near-dialog-toolbar">
        <div class="near-dialog-desc">
          Manage nearby airport relations for the selected city.
        </div>
        <div class="toolbar-actions">
          <el-button type="primary" :icon="Plus" :disabled="!selectedCity" @click="openCreateNearAirport">Add</el-button>
          <el-button :icon="Refresh" :disabled="!selectedCity" @click="loadNearAirports">Refresh</el-button>
        </div>
      </div>

      <el-table
        v-if="selectedCity && (nearAirports.length || nearLoading)"
        v-loading="nearLoading"
        :data="nearAirports"
        border
        row-key="iata_code"
      >
        <el-table-column prop="iata_code" label="IATA" width="110" />
        <el-table-column prop="airport_name" label="Airport Name" min-width="220" />
        <el-table-column label="Distance" width="130">
          <template #default="{ row }">{{ Number(row.distance).toFixed(2) }} km</template>
        </el-table-column>
        <el-table-column label="Actions" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" :icon="Delete" @click="deleteNearAirport(row)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyState
        v-else
        :title="selectedCity ? 'No Nearby Airports' : 'No City Selected'"
        :description="selectedCity ? 'This city has no nearby airport relations.' : 'Select a row from the city list.'"
      />
    </el-dialog>

    <el-dialog
      v-model="cityDialogVisible"
      :title="cityMode === 'create' ? 'Add City' : 'Edit City'"
      width="420px"
      :close-on-click-modal="false"
    >
      <el-form ref="cityFormRef" :model="cityForm" :rules="cityRules" label-position="top">
        <el-form-item label="City Name" prop="city_name">
          <el-input v-model="cityForm.city_name" maxlength="32" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cityDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="submitCity">Save</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="nearDialogVisible"
      title="Add Nearby Airport"
      width="480px"
      :close-on-click-modal="false"
      append-to-body
    >
      <el-form ref="nearFormRef" :model="nearForm" :rules="nearRules" label-position="top">
        <el-form-item label="Airport" prop="iata_code">
          <el-select v-model="nearForm.iata_code" filterable class="full-width">
            <el-option
              v-for="airport in airports"
              :key="airport.iata_code"
              :label="`${airport.iata_code} ${airport.airport_name}`"
              :value="airport.iata_code"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Distance (km)" prop="distance">
          <el-input-number v-model="nearForm.distance" :min="0" :max="300" :precision="2" :step="1" class="full-width" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="nearDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="submitNearAirport">Save</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-crud-page {
  display: grid;
  gap: 16px;
}

.toolbar {
  justify-content: space-between;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.city-search {
  width: 220px;
}

.near-dialog-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
}

.near-dialog-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.near-dialog-desc {
  color: var(--fa-text-secondary);
  font-size: 14px;
}

.full-width {
  width: 100%;
}
</style>
