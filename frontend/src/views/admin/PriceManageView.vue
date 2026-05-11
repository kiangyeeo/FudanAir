<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { Delete, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import { adminApi } from '@/api/admin'
import { flightApi } from '@/api/flight'
import { formatCurrency, formatDate, formatTime } from '@/utils/format'
import type { CabinClass, FareType } from '@/types/common'
import type { CabinPricePayload, FlightInstance } from '@/types/flight'

const cabinClassOptions: CabinClass[] = ['经济舱', '头等舱']
const fareTypeOptions: FareType[] = ['标准', '特价']
const route = useRoute()

const instanceLoading = ref(false)
const priceLoading = ref(false)
const saving = ref(false)
const instances = ref<FlightInstance[]>([])
const selectedInstanceId = ref('')
const selectedInstance = ref<FlightInstance | null>(null)
const prices = ref<CabinPricePayload[]>([])

onMounted(async () => {
  await loadInstances()
  const queryInstanceId = readQueryInstanceId()
  if (queryInstanceId) {
    selectedInstanceId.value = queryInstanceId
    await loadPrices()
  }
})

watch(
  () => route.query.instance_id,
  async () => {
    const queryInstanceId = readQueryInstanceId()
    if (queryInstanceId && queryInstanceId !== selectedInstanceId.value) {
      selectedInstanceId.value = queryInstanceId
      await loadPrices()
    }
  },
)

function readQueryInstanceId() {
  const value = route.query.instance_id
  return typeof value === 'string' ? value : ''
}

async function loadInstances() {
  instanceLoading.value = true
  try {
    const page = await flightApi.listInstances({ page: 1, page_size: 100 })
    instances.value = page.items
  } finally {
    instanceLoading.value = false
  }
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
    cabin_class: '经济舱',
    fare_type: '标准',
    price: 0,
    available_seats: 0,
  })
}

async function removePriceRow(index: number) {
  try {
    await ElMessageBox.confirm('确认删除该档位？保存后才会写入后端。', '删除档位', { type: 'warning' })
    prices.value.splice(index, 1)
  } catch {
    // 取消删除。
  }
}

function validatePrices() {
  if (!prices.value.length) {
    ElMessage.error('至少保留一个舱位定价档位')
    return false
  }
  const keys = new Set<string>()
  for (const row of prices.value) {
    if (row.price < 0 || row.available_seats < 0) {
      ElMessage.error('价格和可售座位不能为负数')
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
    ElMessage.error('请先选择实例')
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
    ElMessage.success('舱位定价已保存')
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
          <el-select
            v-model="selectedInstanceId"
            :loading="instanceLoading"
            clearable
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入实例 ID"
            class="instance-select"
          >
            <el-option
              v-for="instance in instances"
              :key="instance.instance_id"
              :label="`${instance.instance_id} / ${instance.status}`"
              :value="instance.instance_id"
            />
          </el-select>
          <el-button :icon="Search" @click="loadPrices">查询</el-button>
          <el-button :icon="Refresh" @click="loadInstances">刷新实例</el-button>
        </div>
      </div>

      <el-descriptions v-if="selectedInstance" :column="4" border class="instance-summary">
        <el-descriptions-item label="航班号">{{ selectedInstance.flight_no }}</el-descriptions-item>
        <el-descriptions-item label="日期">{{ formatDate(selectedInstance.flight_date) }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ selectedInstance.status }}</el-descriptions-item>
        <el-descriptions-item label="燃油基建费">
          {{ formatCurrency(selectedInstance.fuel_infra_fee ?? null) }}
        </el-descriptions-item>
        <el-descriptions-item label="航线">
          {{ selectedInstance.dep_airport_code }} → {{ selectedInstance.arr_airport_code }}
        </el-descriptions-item>
        <el-descriptions-item label="起飞">{{ formatTime(selectedInstance.scheduled_departure) }}</el-descriptions-item>
        <el-descriptions-item label="到达">{{ formatTime(selectedInstance.scheduled_arrival) }}</el-descriptions-item>
        <el-descriptions-item label="余票">
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
        <el-table-column label="可售座位" width="180">
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
        :title="selectedInstanceId ? '暂无票价档位' : '未选择实例'"
        :description="selectedInstanceId ? '当前实例没有舱位定价档位。' : '选择一个航班实例后维护价格和可售库存。'"
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

.instance-select {
  width: 320px;
}

.instance-summary {
  margin-top: 8px;
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
