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
  base_price: number
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
  { label: 'Mon', value: 1 },
  { label: 'Tue', value: 2 },
  { label: 'Wed', value: 3 },
  { label: 'Thu', value: 4 },
  { label: 'Fri', value: 5 },
  { label: 'Sat', value: 6 },
  { label: 'Sun', value: 7 },
]

const loading = ref(false)
const flights = ref<Flight[]>([])
const total = ref(0)
const airlines = ref<Airline[]>([])
const airports = ref<Airport[]>([])
const aircraftTypes = ref<AircraftType[]>([])
const filters = reactive({
  flight_no: '',
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
  base_price: 0,
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
    { required: true, message: 'Enter flight number', trigger: 'blur' },
    { max: 8, message: 'Flight number cannot exceed 8 characters', trigger: 'blur' },
  ],
  airline_code: [{ required: true, message: 'Select airline', trigger: 'change' }],
  aircraft_model: [{ required: true, message: 'Select aircraft type', trigger: 'change' }],
  dep_airport_code: [{ required: true, message: 'Select departure airport', trigger: 'change' }],
  arr_airport_code: [{ required: true, message: 'Select arrival airport', trigger: 'change' }],
  scheduled_departure: [{ required: true, message: 'Select departure time', trigger: 'change' }],
  scheduled_arrival: [{ required: true, message: 'Select arrival time', trigger: 'change' }],
  fuel_infra_fee: [{ required: true, message: 'Enter fuel & airport fee', trigger: 'change' }],
  base_price: [{ required: true, message: 'Enter base ticket price', trigger: 'change' }],
  weekdays: [{ type: 'array', required: true, min: 1, message: 'Select operating weekdays', trigger: 'change' }],
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
    if (filters.flight_no) {
      params.flight_no = filters.flight_no.trim().toUpperCase()
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
    flight_no: '',
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
    base_price: 0,
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
      base_price: Number(detail.base_price),
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

function validateTimeOrder() {
  if (form.scheduled_departure && form.scheduled_arrival && form.scheduled_departure > form.scheduled_arrival) {
    ElMessage.error('Departure time cannot be later than arrival time')
    return false
  }
  return true
}

function buildPayload(): FlightPayload {
  return {
    scheduled_departure: form.scheduled_departure,
    scheduled_arrival: form.scheduled_arrival,
    fuel_infra_fee: form.fuel_infra_fee,
    base_price: form.base_price,
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
  if (!validateTimeOrder()) {
    return
  }
  const payload = buildPayload()
  if (mode.value === 'create') {
    await adminApi.createFlight({
      ...payload,
      flight_no: form.flight_no.trim().toUpperCase(),
    })
    ElMessage.success('Flight added')
  } else {
    await adminApi.updateFlight(form.flight_no, payload)
    ElMessage.success('Flight updated')
  }
  dialogVisible.value = false
  await loadFlights()
}

async function deleteFlight(row: Flight) {
  try {
    await ElMessageBox.confirm(`Delete flight ${row.flight_no}?`, 'Delete Flight', { type: 'warning' })
    await adminApi.deleteFlight(row.flight_no)
    ElMessage.success('Flight deleted')
    await loadFlights()
  } catch {
    // 取消删除或后端已提示错误。
  }
}
</script>

<template>
  <section class="page-section admin-crud-page">
    <div class="toolbar">
      <h1 class="page-title">Flights</h1>
      <div class="toolbar-actions">
        <el-input
          v-model="filters.flight_no"
          clearable
          :prefix-icon="Search"
          maxlength="8"
          placeholder="Flight no."
          class="flight-no-filter"
          @keyup.enter="applyFilters"
        />
        <el-select v-model="filters.airline_code" clearable filterable placeholder="Airline" class="filter-select">
          <el-option
            v-for="airline in airlines"
            :key="airline.iata_code"
            :label="`${airline.iata_code} ${airline.airline_name}`"
            :value="airline.iata_code"
          />
        </el-select>
        <el-select v-model="filters.dep_airport_code" clearable filterable placeholder="Departure airport" class="filter-select">
          <el-option
            v-for="airport in airports"
            :key="airport.iata_code"
            :label="`${airport.iata_code} ${airport.airport_name}`"
            :value="airport.iata_code"
          />
        </el-select>
        <el-select v-model="filters.arr_airport_code" clearable filterable placeholder="Arrival airport" class="filter-select">
          <el-option
            v-for="airport in airports"
            :key="airport.iata_code"
            :label="`${airport.iata_code} ${airport.airport_name}`"
            :value="airport.iata_code"
          />
        </el-select>
        <el-button :icon="Search" @click="applyFilters">Filter</el-button>
        <el-button @click="resetFilters">Reset</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">Add</el-button>
        <el-button :icon="Refresh" @click="loadFlights">Refresh</el-button>
      </div>
    </div>

    <el-table
      v-if="flights.length || loading"
      v-loading="loading"
      :data="flights"
      class="flight-table"
      border
      row-key="flight_no"
    >
      <el-table-column prop="flight_no" label="Flight No." min-width="120" />
      <el-table-column prop="airline_code" label="Airline" min-width="120" />
      <el-table-column prop="dep_airport_code" label="Departure Airport" min-width="160" />
      <el-table-column prop="arr_airport_code" label="Arrival Airport" min-width="160" />
      <el-table-column label="Departure" min-width="120">
        <template #default="{ row }">{{ formatTime(row.scheduled_departure) }}</template>
      </el-table-column>
      <el-table-column label="Arrival" min-width="120">
        <template #default="{ row }">{{ formatTime(row.scheduled_arrival) }}</template>
      </el-table-column>
      <el-table-column prop="aircraft_model" label="Aircraft Type" min-width="140" />
      <el-table-column label="Ticket Price" min-width="140">
        <template #default="{ row }">{{ formatCurrency(Number(row.base_price)) }}</template>
      </el-table-column>
      <el-table-column label="Fuel & Airport Fee" min-width="140">
        <template #default="{ row }">{{ formatCurrency(Number(row.fuel_infra_fee)) }}</template>
      </el-table-column>
      <el-table-column label="Actions" min-width="180" align="center">
        <template #default="{ row }">
          <el-button link type="primary" :icon="Edit" @click="openEdit(row)">Edit</el-button>
          <el-button link type="danger" :icon="Delete" @click="deleteFlight(row)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>
    <EmptyState v-else title="No Flights" description="No flight data." />

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
      :title="mode === 'create' ? 'Add Flight' : 'Edit Flight'"
      width="760px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" v-loading="dialogLoading" :model="form" :rules="rules" label-position="top">
        <div class="form-grid">
          <el-form-item label="Flight No." prop="flight_no">
            <el-input v-model="form.flight_no" maxlength="8" :disabled="mode === 'edit'" />
          </el-form-item>
          <el-form-item label="Airline" prop="airline_code">
            <el-select v-model="form.airline_code" filterable class="full-width">
              <el-option
                v-for="airline in airlines"
                :key="airline.iata_code"
                :label="`${airline.iata_code} ${airline.airline_name}`"
                :value="airline.iata_code"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Aircraft Type" prop="aircraft_model">
            <el-select v-model="form.aircraft_model" filterable class="full-width">
              <el-option
                v-for="aircraft in aircraftTypes"
                :key="aircraft.model"
                :label="`${aircraft.model} Economy ${aircraft.economy_seats} / First ${aircraft.first_seats}`"
                :value="aircraft.model"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Ticket Price" prop="base_price">
            <el-input-number v-model="form.base_price" :min="0" :precision="2" :step="10" class="full-width" />
            <div class="form-tip">Base economy standard fare before fuel & airport fee. Discount and first class fares are derived automatically.</div>
          </el-form-item>
          <el-form-item label="Fuel & Airport Fee" prop="fuel_infra_fee">
            <el-input-number v-model="form.fuel_infra_fee" :min="0" :precision="2" :step="10" class="full-width" />
          </el-form-item>
          <el-form-item label="Departure Airport" prop="dep_airport_code">
            <el-select v-model="form.dep_airport_code" filterable class="full-width">
              <el-option
                v-for="airport in airports"
                :key="airport.iata_code"
                :label="`${airport.iata_code} ${airport.airport_name}`"
                :value="airport.iata_code"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Departure Terminal" prop="dep_terminal">
            <el-input v-model="form.dep_terminal" maxlength="8" />
          </el-form-item>
          <el-form-item label="Arrival Airport" prop="arr_airport_code">
            <el-select v-model="form.arr_airport_code" filterable class="full-width">
              <el-option
                v-for="airport in airports"
                :key="airport.iata_code"
                :label="`${airport.iata_code} ${airport.airport_name}`"
                :value="airport.iata_code"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Arrival Terminal" prop="arr_terminal">
            <el-input v-model="form.arr_terminal" maxlength="8" />
          </el-form-item>
          <el-form-item label="Scheduled Departure" prop="scheduled_departure">
            <el-time-picker
              v-model="form.scheduled_departure"
              class="full-width"
              format="HH:mm"
              value-format="HH:mm:ss"
              placeholder="Select time"
            />
          </el-form-item>
          <el-form-item label="Scheduled Arrival" prop="scheduled_arrival">
            <el-time-picker
              v-model="form.scheduled_arrival"
              class="full-width"
              format="HH:mm"
              value-format="HH:mm:ss"
              placeholder="Select time"
            />
          </el-form-item>
        </div>

        <el-form-item label="Operating Days" prop="weekdays">
          <el-checkbox-group v-model="form.weekdays">
            <el-checkbox v-for="weekday in weekdayOptions" :key="weekday.value" :label="weekday.value">
              {{ weekday.label }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="Stopovers">
          <div class="stopover-list">
            <div v-for="(_stopover, index) in form.stopovers" :key="index" class="stopover-row">
              <span class="stopover-index">Stop {{ index + 1 }}</span>
              <el-select v-model="form.stopovers[index]" filterable clearable class="stopover-select">
                <el-option
                  v-for="airport in stopoverOptions"
                  :key="airport.iata_code"
                  :label="`${airport.iata_code} ${airport.airport_name}`"
                  :value="airport.iata_code"
                />
              </el-select>
              <el-button :icon="Delete" @click="removeStopover(index)">Delete</el-button>
            </div>
            <el-button :icon="Plus" @click="addStopover">Add Stopover</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="dialogLoading" @click="submit">Save</el-button>
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

.flight-no-filter {
  width: 150px;
}

.flight-table {
  width: 100%;
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

.form-tip {
  margin-top: 4px;
  color: var(--fa-text-secondary);
  font-size: 12px;
  line-height: 1.4;
}
</style>
