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

const cityRows = computed<CityRow[]>(() => cities.value.map((cityName) => ({ city_name: cityName })))

const cityDialogVisible = ref(false)
const cityMode = ref<'create' | 'edit'>('create')
const editingCity = ref('')
const cityFormRef = ref<FormInstance>()
const cityForm = reactive<CityForm>({ city_name: '' })
const cityRules: FormRules<CityForm> = {
  city_name: [
    { required: true, message: '请输入城市名称', trigger: 'blur' },
    { max: 32, message: '城市名称不能超过32个字符', trigger: 'blur' },
  ],
}

const nearDialogVisible = ref(false)
const nearFormRef = ref<FormInstance>()
const nearForm = reactive<NearForm>({ iata_code: '', distance: 0 })
const nearRules: FormRules<NearForm> = {
  iata_code: [{ required: true, message: '请选择机场', trigger: 'change' }],
  distance: [{ required: true, message: '请输入距离', trigger: 'change' }],
}

onMounted(async () => {
  await Promise.all([loadCities(), loadAirports()])
})

async function loadCities() {
  loading.value = true
  try {
    cities.value = await flightApi.listCities()
    if (!selectedCity.value && cities.value.length) {
      selectedCity.value = cities.value[0]
      await loadNearAirports()
    } else if (selectedCity.value && !cities.value.includes(selectedCity.value)) {
      selectedCity.value = ''
      nearAirports.value = []
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

function selectCity(row: CityRow) {
  selectedCity.value = row.city_name
  void loadNearAirports()
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
    ElMessage.success('城市已新增')
  } else {
    await adminApi.updateCity(editingCity.value, { city_name: cityName })
    selectedCity.value = cityName
    ElMessage.success('城市已更新')
  }
  cityDialogVisible.value = false
  await loadCities()
}

async function deleteCity(row: CityRow) {
  try {
    await ElMessageBox.confirm(`确认删除城市 ${row.city_name}？`, '删除城市', { type: 'warning' })
    await adminApi.deleteCity(row.city_name)
    if (selectedCity.value === row.city_name) {
      selectedCity.value = ''
      nearAirports.value = []
    }
    ElMessage.success('城市已删除')
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
  ElMessage.success('临近机场已新增')
  await loadNearAirports()
}

async function deleteNearAirport(row: NearAirport) {
  try {
    await ElMessageBox.confirm(`确认删除 ${selectedCity.value} 与 ${row.iata_code} 的关系？`, '删除临近机场', { type: 'warning' })
    await adminApi.deleteNearAirport(selectedCity.value, row.iata_code)
    ElMessage.success('临近机场已删除')
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
        <h1 class="page-title">城市管理</h1>
        <div class="toolbar-actions">
          <el-button type="primary" :icon="Plus" @click="openCreateCity">新增</el-button>
          <el-button :icon="Refresh" @click="loadCities">刷新</el-button>
        </div>
      </div>

      <el-table
        v-if="cityRows.length || loading"
        v-loading="loading"
        :data="cityRows"
        border
        row-key="city_name"
        highlight-current-row
      >
        <el-table-column prop="city_name" label="城市名称" min-width="180" />
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Search" @click="selectCity(row)">临近机场</el-button>
            <el-button link type="primary" :icon="Edit" @click="openEditCity(row)">编辑</el-button>
            <el-button link type="danger" :icon="Delete" @click="deleteCity(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else title="暂无城市" description="城市数据为空。" />
    </section>

    <section class="page-section">
      <div class="toolbar">
        <h2 class="section-title">临近机场</h2>
        <el-tag v-if="selectedCity" type="info">{{ selectedCity }}</el-tag>
        <div class="toolbar-actions">
          <el-button type="primary" :icon="Plus" :disabled="!selectedCity" @click="openCreateNearAirport">新增</el-button>
          <el-button :icon="Refresh" :disabled="!selectedCity" @click="loadNearAirports">刷新</el-button>
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
        <el-table-column prop="airport_name" label="机场名称" min-width="220" />
        <el-table-column label="距离" width="130">
          <template #default="{ row }">{{ Number(row.distance).toFixed(2) }} km</template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" :icon="Delete" @click="deleteNearAirport(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState
        v-else
        :title="selectedCity ? '暂无临近机场' : '未选择城市'"
        :description="selectedCity ? '当前城市没有临近机场关系。' : '从城市列表选择一行。'"
      />
    </section>

    <el-dialog
      v-model="cityDialogVisible"
      :title="cityMode === 'create' ? '新增城市' : '编辑城市'"
      width="420px"
      :close-on-click-modal="false"
    >
      <el-form ref="cityFormRef" :model="cityForm" :rules="cityRules" label-position="top">
        <el-form-item label="城市名称" prop="city_name">
          <el-input v-model="cityForm.city_name" maxlength="32" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cityDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCity">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="nearDialogVisible"
      title="新增临近机场"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form ref="nearFormRef" :model="nearForm" :rules="nearRules" label-position="top">
        <el-form-item label="机场" prop="iata_code">
          <el-select v-model="nearForm.iata_code" filterable class="full-width">
            <el-option
              v-for="airport in airports"
              :key="airport.iata_code"
              :label="`${airport.iata_code} ${airport.airport_name}`"
              :value="airport.iata_code"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="距离 km" prop="distance">
          <el-input-number v-model="nearForm.distance" :min="0" :max="300" :precision="2" :step="1" class="full-width" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="nearDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitNearAirport">保存</el-button>
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

.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.full-width {
  width: 100%;
}
</style>
