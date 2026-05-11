<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import EmptyState from '@/components/common/EmptyState.vue'
import { adminApi } from '@/api/admin'
import { flightApi } from '@/api/flight'
import { formatCurrency, formatTime } from '@/utils/format'
import type { AircraftType, Airline, Airport, Flight, FlightListParams, FlightPayload } from '@/types/flight'

interface FlightForm {
  flight_no: string
  scheduled_departure: string
  scheduled_arrival: string
  fuel_infra_fee: number
  dep_airport_code: string
  dep_terminal: string
  arr_airport_code: string
  arr_terminal: string
  airline_code: string
  aircraft_model: string
  weekdays: number[]
  stopovers: string[]
}

const weekdayOptions = [
  { label: '周一', value: 1 },
  { label: '周二', value: 2 },
  { label: '周三', value: 3 },
  { label: '周四', value: 4 },
  { label: '周五', value: 5 },
  { label: '周六', value: 6 },
  { label: '周日', value: 7 },
]

const loading = ref(false)
const flights = ref<Flight[]>([])
const total = ref(0)
const airlines = ref<Airline[]>([])
const airports = ref<Airport[]>([])
const aircraftTypes = ref<AircraftType[]>([])
const filters = reactive({
  airline_code: '',
  dep_airport_code: '',
  arr_airport_code: '',
})
const pagination = reactive({
  page: 1,
  pageSize: 20,
})

const dialogVisible = ref(false)
const dialogLoading = ref(false)
const mode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()
const form = reactive<FlightForm>({
  flight_no: '',
  scheduled_departure: '',
  scheduled_arrival: '',
  fuel_infra_fee: 0,
  dep_airport_code: '',
  dep_terminal: '',
  arr_airport_code: '',
  arr_terminal: '',
  airline_code: '',
  aircraft_model: '',
  weekdays: [],
  stopovers: [],
})

const rules: FormRules<FlightForm> = {
  flight_no: [
    { required: true, message: '请输入航班号', trigger: 'blur' },
    { max: 8, message: '航班号不能超过8个字符', trigger: 'blur' },
  ],
  airline_code: [{ required: true, message: '请选择航司', trigger: 'change' }],
  aircraft_model: [{ required: true, message: '请选择机型', trigger: 'change' }],
  dep_airport_code: [{ required: true, message: '请选择起飞机场', trigger: 'change' }],
  arr_airport_code: [{ required: true, message: '请选择到达机场', trigger: 'change' }],
  scheduled_departure: [{ required: true, message: '请选择起飞时间', trigger: 'change' }],
  scheduled_arrival: [{ required: true, message: '请选择到达时间', trigger: 'change' }],
  fuel_infra_fee: [{ required: true, message: '请输入燃油基建费', trigger: 'change' }],
  weekdays: [{ type: 'array', required: true, min: 1, message: '请选择飞行日', trigger: 'change' }],
}

const stopoverOptions = computed(() =>
  airports.value.filter(
    (airport) => airport.iata_code !== form.dep_airport_code && airport.iata_code !== form.arr_airport_code,
  ),
)

onMounted(async () => {
  await Promise.all([loadReferences(), loadFlights()])
})

async function loadReferences() {
  const [airlineRows, airportRows, aircraftRows] = await Promise.all([
    flightApi.listAirlines(),
    flightApi.listAirports(),
    flightApi.listAircraftTypes(),
  ])
  airlines.value = airlineRows
  airports.value = airportRows
  aircraftTypes.value = aircraftRows
}

async function loadFlights() {
  loading.value = true
  try {
    const params: FlightListParams = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.airline_code) {
      params.airline_code = filters.airline_code
    }
    if (filters.dep_airport_code) {
      params.dep_airport_code = filters.dep_airport_code
    }
    if (filters.arr_airport_code) {
      params.arr_airport_code = filters.arr_airport_code
    }
    const page = await flightApi.listFlights(params)
    flights.value = page.items
    total.value = page.total
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  Object.assign(filters, {
    airline_code: '',
    dep_airport_code: '',
    arr_airport_code: '',
  })
  pagination.page = 1
  void loadFlights()
}

function applyFilters() {
  pagination.page = 1
  void loadFlights()
}

function handlePageSizeChange(size: number) {
  pagination.pageSize = size
  pagination.page = 1
  void loadFlights()
}

function resetForm() {
  Object.assign(form, {
    flight_no: '',
    scheduled_departure: '',
    scheduled_arrival: '',
    fuel_infra_fee: 0,
    dep_airport_code: '',
    dep_terminal: '',
    arr_airport_code: '',
    arr_terminal: '',
    airline_code: '',
    aircraft_model: '',
    weekdays: [],
    stopovers: [],
  })
}

function openCreate() {
  mode.value = 'create'
  resetForm()
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

async function openEdit(row: Flight) {
  mode.value = 'edit'
  resetForm()
  dialogLoading.value = true
  dialogVisible.value = true
  try {
    const detail = await flightApi.getFlight(row.flight_no)
    Object.assign(form, {
      flight_no: detail.flight_no,
      scheduled_departure: detail.scheduled_departure,
      scheduled_arrival: detail.scheduled_arrival,
      fuel_infra_fee: Number(detail.fuel_infra_fee),
      dep_airport_code: detail.dep_airport_code,
      dep_terminal: detail.dep_terminal || '',
      arr_airport_code: detail.arr_airport_code,
      arr_terminal: detail.arr_terminal || '',
      airline_code: detail.airline_code,
      aircraft_model: detail.aircraft_model,
      weekdays: [...(detail.weekdays || [])],
      stopovers: [...(detail.stopovers || [])],
    })
    formRef.value?.clearValidate()
  } finally {
    dialogLoading.value = false
  }
}

function addStopover() {
  form.stopovers.push('')
}

function removeStopover(index: number) {
  form.stopovers.splice(index, 1)
}

function buildPayload(): FlightPayload {
  return {
    scheduled_departure: form.scheduled_departure,
    scheduled_arrival: form.scheduled_arrival,
    fuel_infra_fee: form.fuel_infra_fee,
    dep_airport_code: form.dep_airport_code.trim().toUpperCase(),
    dep_terminal: form.dep_terminal.trim() || null,
    arr_airport_code: form.arr_airport_code.trim().toUpperCase(),
    arr_terminal: form.arr_terminal.trim() || null,
    airline_code: form.airline_code.trim().toUpperCase(),
    aircraft_model: form.aircraft_model.trim().toUpperCase(),
    weekdays: [...form.weekdays].sort((left, right) => left - right),
    stopovers: form.stopovers.map((code) => code.trim().toUpperCase()).filter(Boolean),
  }
}

async function submit() {
  await formRef.value?.validate()
  const payload = buildPayload()
  if (mode.value === 'create') {
    await adminApi.createFlight({
      ...payload,
      flight_no: form.flight_no.trim().toUpperCase(),
    })
    ElMessage.success('航班已新增')
  } else {
    await adminApi.updateFlight(form.flight_no, payload)
    ElMessage.success('航班已更新')
  }
  dialogVisible.value = false
  await loadFlights()
}

async function deleteFlight(row: Flight) {
  try {
    await ElMessageBox.confirm(`确认删除航班 ${row.flight_no}？`, '删除航班', { type: 'warning' })
    await adminApi.deleteFlight(row.flight_no)
    ElMessage.success('航班已删除')
    await loadFlights()
  } catch {
    // 取消删除或后端已提示错误。
  }
}
</script>

<template>
  <section class="page-section admin-crud-page">
    <div class="toolbar">
      <h1 class="page-title">航班管理</h1>
      <div class="toolbar-actions">
        <el-select v-model="filters.airline_code" clearable filterable placeholder="航司" class="filter-select">
          <el-option
            v-for="airline in airlines"
            :key="airline.iata_code"
            :label="`${airline.iata_code} ${airline.airline_name}`"
            :value="airline.iata_code"
          />
        </el-select>
        <el-select v-model="filters.dep_airport_code" clearable filterable placeholder="起飞机场" class="filter-select">
          <el-option
            v-for="airport in airports"
            :key="airport.iata_code"
            :label="`${airport.iata_code} ${airport.airport_name}`"
            :value="airport.iata_code"
          />
        </el-select>
        <el-select v-model="filters.arr_airport_code" clearable filterable placeholder="到达机场" class="filter-select">
          <el-option
            v-for="airport in airports"
            :key="airport.iata_code"
            :label="`${airport.iata_code} ${airport.airport_name}`"
            :value="airport.iata_code"
          />
        </el-select>
        <el-button :icon="Search" @click="applyFilters">筛选</el-button>
        <el-button @click="resetFilters">重置</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
        <el-button :icon="Refresh" @click="loadFlights">刷新</el-button>
      </div>
    </div>

    <el-table v-if="flights.length || loading" v-loading="loading" :data="flights" border row-key="flight_no">
      <el-table-column prop="flight_no" label="航班号" width="110" />
      <el-table-column prop="airline_code" label="航司" width="90" />
      <el-table-column prop="dep_airport_code" label="起飞机场" width="110" />
      <el-table-column prop="arr_airport_code" label="到达机场" width="110" />
      <el-table-column label="起飞" width="100">
        <template #default="{ row }">{{ formatTime(row.scheduled_departure) }}</template>
      </el-table-column>
      <el-table-column label="到达" width="100">
        <template #default="{ row }">{{ formatTime(row.scheduled_arrival) }}</template>
      </el-table-column>
      <el-table-column prop="aircraft_model" label="机型" width="130" />
      <el-table-column label="燃油基建费" width="120">
        <template #default="{ row }">{{ formatCurrency(Number(row.fuel_infra_fee)) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" :icon="Delete" @click="deleteFlight(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <EmptyState v-else title="暂无航班" description="航班数据为空。" />

    <el-pagination
      v-if="total > 0"
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.pageSize"
      class="pager"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      layout="total, sizes, prev, pager, next"
      @current-change="loadFlights"
      @size-change="handlePageSizeChange"
    />

    <el-dialog
      v-model="dialogVisible"
      :title="mode === 'create' ? '新增航班' : '编辑航班'"
      width="760px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" v-loading="dialogLoading" :model="form" :rules="rules" label-position="top">
        <div class="form-grid">
          <el-form-item label="航班号" prop="flight_no">
            <el-input v-model="form.flight_no" maxlength="8" :disabled="mode === 'edit'" />
          </el-form-item>
          <el-form-item label="航司" prop="airline_code">
            <el-select v-model="form.airline_code" filterable class="full-width">
              <el-option
                v-for="airline in airlines"
                :key="airline.iata_code"
                :label="`${airline.iata_code} ${airline.airline_name}`"
                :value="airline.iata_code"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="机型" prop="aircraft_model">
            <el-select v-model="form.aircraft_model" filterable class="full-width">
              <el-option
                v-for="aircraft in aircraftTypes"
                :key="aircraft.model"
                :label="`${aircraft.model} 经济舱${aircraft.economy_seats} / 头等舱${aircraft.first_seats}`"
                :value="aircraft.model"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="燃油基建费" prop="fuel_infra_fee">
            <el-input-number v-model="form.fuel_infra_fee" :min="0" :precision="2" :step="10" class="full-width" />
          </el-form-item>
          <el-form-item label="起飞机场" prop="dep_airport_code">
            <el-select v-model="form.dep_airport_code" filterable class="full-width">
              <el-option
                v-for="airport in airports"
                :key="airport.iata_code"
                :label="`${airport.iata_code} ${airport.airport_name}`"
                :value="airport.iata_code"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="起飞航站楼" prop="dep_terminal">
            <el-input v-model="form.dep_terminal" maxlength="8" />
          </el-form-item>
          <el-form-item label="到达机场" prop="arr_airport_code">
            <el-select v-model="form.arr_airport_code" filterable class="full-width">
              <el-option
                v-for="airport in airports"
                :key="airport.iata_code"
                :label="`${airport.iata_code} ${airport.airport_name}`"
                :value="airport.iata_code"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="到达航站楼" prop="arr_terminal">
            <el-input v-model="form.arr_terminal" maxlength="8" />
          </el-form-item>
          <el-form-item label="计划起飞" prop="scheduled_departure">
            <el-time-picker
              v-model="form.scheduled_departure"
              class="full-width"
              format="HH:mm"
              value-format="HH:mm:ss"
              placeholder="选择时间"
            />
          </el-form-item>
          <el-form-item label="计划到达" prop="scheduled_arrival">
            <el-time-picker
              v-model="form.scheduled_arrival"
              class="full-width"
              format="HH:mm"
              value-format="HH:mm:ss"
              placeholder="选择时间"
            />
          </el-form-item>
        </div>

        <el-form-item label="飞行日" prop="weekdays">
          <el-checkbox-group v-model="form.weekdays">
            <el-checkbox v-for="weekday in weekdayOptions" :key="weekday.value" :label="weekday.value">
              {{ weekday.label }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="经停机场">
          <div class="stopover-list">
            <div v-for="(_stopover, index) in form.stopovers" :key="index" class="stopover-row">
              <span class="stopover-index">第 {{ index + 1 }} 站</span>
              <el-select v-model="form.stopovers[index]" filterable clearable class="stopover-select">
                <el-option
                  v-for="airport in stopoverOptions"
                  :key="airport.iata_code"
                  :label="`${airport.iata_code} ${airport.airport_name}`"
                  :value="airport.iata_code"
                />
              </el-select>
              <el-button :icon="Delete" @click="removeStopover(index)">删除</el-button>
            </div>
            <el-button :icon="Plus" @click="addStopover">添加经停</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="dialogLoading" @click="submit">保存</el-button>
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
  width: 170px;
}

.pager {
  justify-self: end;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 14px;
}

.full-width {
  width: 100%;
}

.stopover-list {
  display: grid;
  width: 100%;
  gap: 8px;
}

.stopover-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) 82px;
  gap: 8px;
  align-items: center;
}

.stopover-index {
  color: var(--fa-text-secondary);
  font-size: 13px;
}

.stopover-select {
  width: 100%;
}
</style>
