<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { Delete, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import { adminApi } from '@/api/admin'
import { flightApi } from '@/api/flight'
import { formatCurrency, formatDate, formatTime } from '@/utils/format'
import type { CabinClass, FareType } from '@/types/common'
import type { CabinPricePayload, FlightInstance, FlightInstanceListParams } from '@/types/flight'

const cabinClassOptions: CabinClass[] = ['经济舱', '头等舱']
const fareTypeOptions: FareType[] = ['标准', '特价']
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
    cabin_class: cabinClassOptions[0],
    fare_type: fareTypeOptions[0],
    price: 0,
    available_seats: 0,
  })
}

async function removePriceRow(index: number) {
  try {
    await ElMessageBox.confirm('确认删除该票价档位？如果已有客票引用，保存时会被后端拒绝。', '删除档位', { type: 'warning' })
    prices.value.splice(index, 1)
  } catch {
    // 用户取消删除
  }
}

function validatePrices() {
  if (!prices.value.length) {
    ElMessage.error('请至少保留一个票价档位')
    return false
  }
  const keys = new Set<string>()
  for (const row of prices.value) {
    if (row.price < 0 || row.available_seats < 0) {
      ElMessage.error('价格和剩余数量不能为负')
      return false
    }
    const key = `${row.cabin_class}-${row.fare_type}`
    if (keys.has(key)) {
      ElMessage.error('舱位和票价类型不能重复')
      return false
    }
    keys.add(key)
  }
  return true
}

async function savePrices() {
  const instanceId = selectedInstanceId.value.trim()
  if (!instanceId) {
    ElMessage.error('请选择航班实例')
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
    ElMessage.success('票价和余票已保存')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="price-page">
    <section class="page-section">
      <div class="toolbar">
        <h1 class="page-title">票价管理</h1>
        <div class="toolbar-actions">
          <el-input
            v-model="filters.flight_no"
            clearable
            :prefix-icon="Search"
            maxlength="8"
            placeholder="航班号"
            class="flight-filter"
            @keyup.enter="applyFilters"
          />
          <el-date-picker
            v-model="filters.flight_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="运行日期"
            class="date-filter"
          />
          <el-button :icon="Search" @click="applyFilters">查询实例</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button :icon="Refresh" @click="loadInstances">刷新</el-button>
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
        <el-table-column prop="instance_id" label="实例 ID" min-width="180" />
        <el-table-column prop="flight_no" label="航班号" width="110" />
        <el-table-column label="运行日期" width="130">
          <template #default="{ row }">{{ formatDate(row.flight_date) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="economy_left" label="经济舱余票" width="120" />
        <el-table-column prop="first_left" label="头等舱余票" width="120" />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :disabled="selectedInstanceId === row.instance_id" @click="selectInstance(row)">
              调整
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else title="暂无航班实例" description="按航班号和运行日期查询要调整的航班实例。" />

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
        <el-descriptions-item label="航班号">{{ selectedInstance.flight_no }}</el-descriptions-item>
        <el-descriptions-item label="运行日期">{{ formatDate(selectedInstance.flight_date) }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ selectedInstance.status }}</el-descriptions-item>
        <el-descriptions-item label="燃油基建费">
          {{ formatCurrency(selectedInstance.fuel_infra_fee ?? null) }}
        </el-descriptions-item>
        <el-descriptions-item label="航线">
          {{ selectedInstance.dep_airport_code }} -> {{ selectedInstance.arr_airport_code }}
        </el-descriptions-item>
        <el-descriptions-item label="起飞">{{ formatTime(selectedInstance.scheduled_departure) }}</el-descriptions-item>
        <el-descriptions-item label="到达">{{ formatTime(selectedInstance.scheduled_arrival) }}</el-descriptions-item>
        <el-descriptions-item label="汇总余票">
          经济舱 {{ selectedInstance.economy_left }} / 头等舱 {{ selectedInstance.first_left }}
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <section class="page-section admin-crud-page">
      <div class="toolbar">
        <h2 class="section-title">舱位定价档位</h2>
        <div class="toolbar-actions">
          <el-button type="primary" :icon="Plus" :disabled="!selectedInstanceId" @click="addPriceRow">新增档位</el-button>
          <el-button :icon="Refresh" :disabled="!selectedInstanceId" @click="loadPrices">刷新</el-button>
          <el-button type="primary" :loading="saving" :disabled="!selectedInstanceId || !prices.length" @click="savePrices">
            保存
          </el-button>
        </div>
      </div>

      <el-table v-if="prices.length || priceLoading" v-loading="priceLoading" :data="prices" border>
        <el-table-column label="舱位" width="150">
          <template #default="{ row }">
            <el-select v-model="row.cabin_class" class="full-width">
              <el-option v-for="cabinClass in cabinClassOptions" :key="cabinClass" :label="cabinClass" :value="cabinClass" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="票价类型" width="150">
          <template #default="{ row }">
            <el-select v-model="row.fare_type" class="full-width">
              <el-option v-for="fareType in fareTypeOptions" :key="fareType" :label="fareType" :value="fareType" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="价格" width="180">
          <template #default="{ row }">
            <el-input-number v-model="row.price" :min="0" :precision="2" :step="50" class="full-width" />
          </template>
        </el-table-column>
        <el-table-column label="剩余数量" width="180">
          <template #default="{ row }">
            <el-input-number v-model="row.available_seats" :min="0" :precision="0" :step="1" class="full-width" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ $index }">
            <el-button link type="danger" :icon="Delete" @click="removePriceRow($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState
        v-else
        :title="selectedInstanceId ? '暂无票价档位' : '未选择航班实例'"
        :description="selectedInstanceId ? '当前实例还没有舱位定价档位。' : '先按航班号和运行日期选择航班实例。'"
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
