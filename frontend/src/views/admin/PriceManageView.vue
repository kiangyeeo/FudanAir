<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { Delete, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import { adminApi } from '@/api/admin'
import { flightApi } from '@/api/flight'
import { formatCurrency, formatDate, formatTime } from '@/utils/format'
import { cabinClassOptions, fareTypeOptions, instanceStatusLabel } from '@/utils/labels'
import type { CabinClass, FareType } from '@/types/common'
import type { CabinPricePayload, FlightInstance, FlightInstanceListParams } from '@/types/flight'

const route = useRoute()

const instanceLoading = ref(false)
const priceLoading = ref(false)
const saving = ref(false)
const instances = ref<FlightInstance[]>([])
const instanceTotal = ref(0)
const selectedInstanceId = ref('')
const selectedInstance = ref<FlightInstance | null>(null)
const prices = ref<CabinPricePayload[]>([])

const filters = reactive({
  flight_no: '',
  flight_date: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
})

onMounted(async () => {
  const queryInstanceId = readQueryInstanceId()
  if (queryInstanceId) {
    selectedInstanceId.value = queryInstanceId
    applyInstanceIdToFilters(queryInstanceId)
  }
  await loadInstances()
  if (queryInstanceId) {
    await loadPrices()
  }
})

watch(
  () => route.query.instance_id,
  async () => {
    const queryInstanceId = readQueryInstanceId()
    if (!queryInstanceId || queryInstanceId === selectedInstanceId.value) {
      return
    }
    selectedInstanceId.value = queryInstanceId
    applyInstanceIdToFilters(queryInstanceId)
    pagination.page = 1
    await loadInstances()
    await loadPrices()
  },
)

function readQueryInstanceId() {
  const value = route.query.instance_id
  return typeof value === 'string' ? value : ''
}

function applyInstanceIdToFilters(instanceId: string) {
  const match = instanceId.match(/^(.+)_([0-9]{8})$/)
  if (!match) {
    return
  }
  filters.flight_no = match[1]
  const rawDate = match[2]
  filters.flight_date = `${rawDate.slice(0, 4)}-${rawDate.slice(4, 6)}-${rawDate.slice(6, 8)}`
}

function normalizeFlightNo(value: string) {
  return value.trim().toUpperCase()
}

async function loadInstances() {
  instanceLoading.value = true
  try {
    const params: FlightInstanceListParams = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    const flightNo = normalizeFlightNo(filters.flight_no)
    if (flightNo) {
      params.flight_no = flightNo
    }
    if (filters.flight_date) {
      params.flight_date = filters.flight_date
    }
    const page = await flightApi.listInstances(params)
    instances.value = page.items
    instanceTotal.value = page.total
  } finally {
    instanceLoading.value = false
  }
}

async function applyFilters() {
  pagination.page = 1
  await loadInstances()
  if (filters.flight_no && filters.flight_date && instances.value.length === 1) {
    await selectInstance(instances.value[0])
  }
}

function resetFilters() {
  Object.assign(filters, {
    flight_no: '',
    flight_date: '',
  })
  pagination.page = 1
  void loadInstances()
}

function handlePageSizeChange(size: number) {
  pagination.pageSize = size
  pagination.page = 1
  void loadInstances()
}

async function selectInstance(row: FlightInstance) {
  selectedInstanceId.value = row.instance_id
  await loadPrices()
}

async function loadPrices() {
  const instanceId = selectedInstanceId.value.trim()
  if (!instanceId) {
    selectedInstance.value = null
    prices.value = []
    return
  }
  priceLoading.value = true
  try {
    const [instance, rows] = await Promise.all([
      flightApi.getInstance(instanceId),
      flightApi.listCabinPrices(instanceId),
    ])
    selectedInstance.value = instance
    prices.value = rows.map((row) => ({
      cabin_class: row.cabin_class,
      fare_type: row.fare_type,
      price: Number(row.price),
      available_seats: Number(row.available_seats),
    }))
  } finally {
    priceLoading.value = false
  }
}

function addPriceRow() {
  prices.value.push({
    cabin_class: cabinClassOptions[0].value,
    fare_type: fareTypeOptions[0].value,
    price: 0,
    available_seats: 0,
  })
}

async function removePriceRow(index: number) {
  try {
    await ElMessageBox.confirm('Delete this fare tier? The backend will reject the save if existing tickets reference it.', 'Delete Fare Tier', { type: 'warning' })
    prices.value.splice(index, 1)
  } catch {
    // 用户取消删除
  }
}

function validatePrices() {
  if (!prices.value.length) {
    ElMessage.error('Keep at least one fare tier')
    return false
  }
  const keys = new Set<string>()
  for (const row of prices.value) {
    if (row.price < 0 || row.available_seats < 0) {
      ElMessage.error('Price and remaining seats cannot be negative')
      return false
    }
    const key = `${row.cabin_class}-${row.fare_type}`
    if (keys.has(key)) {
      ElMessage.error('Cabin and fare type cannot be duplicated')
      return false
    }
    keys.add(key)
  }
  return true
}

async function savePrices() {
  const instanceId = selectedInstanceId.value.trim()
  if (!instanceId) {
    ElMessage.error('Select a flight instance')
    return
  }
  if (!validatePrices()) {
    return
  }
  saving.value = true
  try {
    const rows = await adminApi.replaceCabinPrices(instanceId, {
      cabin_prices: prices.value.map((row) => ({
        cabin_class: row.cabin_class,
        fare_type: row.fare_type,
        price: row.price,
        available_seats: row.available_seats,
      })),
    })
    prices.value = rows.map((row) => ({
      cabin_class: row.cabin_class,
      fare_type: row.fare_type,
      price: Number(row.price),
      available_seats: Number(row.available_seats),
    }))
    selectedInstance.value = await flightApi.getInstance(instanceId)
    await loadInstances()
    ElMessage.success('Fares and seats saved')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="price-page">
    <section class="page-section">
      <div class="toolbar">
        <h1 class="page-title">Pricing</h1>
        <div class="toolbar-actions">
          <el-input
            v-model="filters.flight_no"
            clearable
            :prefix-icon="Search"
            maxlength="8"
            placeholder="Flight no."
            class="flight-filter"
            @keyup.enter="applyFilters"
          />
          <el-date-picker
            v-model="filters.flight_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="Operating date"
            class="date-filter"
          />
          <el-button :icon="Search" @click="applyFilters">Search Instances</el-button>
          <el-button @click="resetFilters">Reset</el-button>
          <el-button :icon="Refresh" @click="loadInstances">Refresh</el-button>
        </div>
      </div>

      <el-table
        v-if="instances.length || instanceLoading"
        v-loading="instanceLoading"
        :data="instances"
        border
        row-key="instance_id"
        class="instance-table"
        @row-dblclick="selectInstance"
      >
        <el-table-column prop="instance_id" label="Instance ID" min-width="180" />
        <el-table-column prop="flight_no" label="Flight No." width="110" />
        <el-table-column label="Operating Date" width="130">
          <template #default="{ row }">{{ formatDate(row.flight_date) }}</template>
        </el-table-column>
        <el-table-column label="Status" width="120">
          <template #default="{ row }">{{ instanceStatusLabel(row.status) }}</template>
        </el-table-column>
        <el-table-column prop="economy_left" label="Economy Left" width="120" />
        <el-table-column prop="first_left" label="First Left" width="120" />
        <el-table-column label="Actions" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :disabled="selectedInstanceId === row.instance_id" @click="selectInstance(row)">
              Adjust
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else title="No Flight Instances" description="Search by flight number and operating date to adjust an instance." />

      <el-pagination
        v-if="instanceTotal > 0"
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        class="pager"
        :page-sizes="[10, 20, 50, 100]"
        :total="instanceTotal"
        layout="total, sizes, prev, pager, next"
        @current-change="loadInstances"
        @size-change="handlePageSizeChange"
      />

      <el-descriptions v-if="selectedInstance" :column="4" border class="instance-summary">
        <el-descriptions-item label="Flight No.">{{ selectedInstance.flight_no }}</el-descriptions-item>
        <el-descriptions-item label="Operating Date">{{ formatDate(selectedInstance.flight_date) }}</el-descriptions-item>
        <el-descriptions-item label="Status">{{ instanceStatusLabel(selectedInstance.status) }}</el-descriptions-item>
        <el-descriptions-item label="Fuel & Airport Fee">
          {{ formatCurrency(selectedInstance.fuel_infra_fee ?? null) }}
        </el-descriptions-item>
        <el-descriptions-item label="Route">
          {{ selectedInstance.dep_airport_code }} -> {{ selectedInstance.arr_airport_code }}
        </el-descriptions-item>
        <el-descriptions-item label="Departure">{{ formatTime(selectedInstance.scheduled_departure) }}</el-descriptions-item>
        <el-descriptions-item label="Arrival">{{ formatTime(selectedInstance.scheduled_arrival) }}</el-descriptions-item>
        <el-descriptions-item label="Seat Summary">
          Economy {{ selectedInstance.economy_left }} / First {{ selectedInstance.first_left }}
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <section class="page-section admin-crud-page">
      <div class="toolbar">
        <h2 class="section-title">Cabin Fare Tiers</h2>
        <div class="toolbar-actions">
          <el-button type="primary" :icon="Plus" :disabled="!selectedInstanceId" @click="addPriceRow">Add Tier</el-button>
          <el-button :icon="Refresh" :disabled="!selectedInstanceId" @click="loadPrices">Refresh</el-button>
          <el-button type="primary" :loading="saving" :disabled="!selectedInstanceId || !prices.length" @click="savePrices">
            Save
          </el-button>
        </div>
      </div>

      <el-table v-if="prices.length || priceLoading" v-loading="priceLoading" :data="prices" border>
        <el-table-column label="Cabin" width="150">
          <template #default="{ row }">
            <el-select v-model="row.cabin_class" class="full-width">
              <el-option v-for="item in cabinClassOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="Fare Type" width="150">
          <template #default="{ row }">
            <el-select v-model="row.fare_type" class="full-width">
              <el-option v-for="item in fareTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="Price" width="180">
          <template #default="{ row }">
            <el-input-number v-model="row.price" :min="0" :precision="2" :step="50" class="full-width" />
          </template>
        </el-table-column>
        <el-table-column label="Seats Left" width="180">
          <template #default="{ row }">
            <el-input-number v-model="row.available_seats" :min="0" :precision="0" :step="1" class="full-width" />
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="110" fixed="right">
          <template #default="{ $index }">
            <el-button link type="danger" :icon="Delete" @click="removePriceRow($index)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState
        v-else
        :title="selectedInstanceId ? 'No Fare Tiers' : 'No Flight Instance Selected'"
        :description="selectedInstanceId ? 'This instance has no cabin fare tiers.' : 'Select a flight instance by flight number and operating date first.'"
      />
    </section>
  </div>
</template>

<style scoped>
.price-page {
  display: grid;
  gap: 16px;
}

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

.flight-filter {
  width: 150px;
}

.date-filter {
  width: 150px;
}

.instance-table {
  margin-top: 8px;
}

.pager {
  justify-self: end;
  margin-top: 8px;
}

.instance-summary {
  margin-top: 12px;
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
