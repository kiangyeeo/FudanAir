<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import { adminApi } from '@/api/admin'
import { flightApi } from '@/api/flight'
import { formatCurrency, formatDate, formatTime } from '@/utils/format'
import { instanceStatusLabel, instanceStatusOptions } from '@/utils/labels'
import type {
  FlightInstance,
  FlightInstanceBatchPayload,
  FlightInstanceListParams,
  InstanceStatus,
} from '@/types/flight'

interface CreateForm {
  flight_no: string
  flight_date: string
}

interface BatchForm {
  flight_no: string
  start_date: string
  end_date: string
}

interface UpdateForm {
  instance_id: string
  flight_no: string
  scheduled_departure: string
  scheduled_arrival: string
  fuel_infra_fee: number
}
interface StatusForm {
  instance_id: string
  status: InstanceStatus
}

const router = useRouter()

const loading = ref(false)
const instances = ref<FlightInstance[]>([])
const total = ref(0)
const filters = reactive({
  flight_no: '',
  flight_date: '',
  status: '',
})
const pagination = reactive({
  page: 1,
  pageSize: 20,
})

const createDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()
const createForm = reactive<CreateForm>({
  flight_no: '',
  flight_date: '',
})

const batchDialogVisible = ref(false)
const batchFormRef = ref<FormInstance>()
const batchForm = reactive<BatchForm>({
  flight_no: '',
  start_date: '',
  end_date: '',
})

const updateDialogVisible = ref(false)
const updateFormRef = ref<FormInstance>()
const updateForm = reactive<UpdateForm>({
  instance_id: '',
  flight_no: '',
  scheduled_departure: '',
  scheduled_arrival: '',
  fuel_infra_fee: 0,
})
const statusDialogVisible = ref(false)
const statusFormRef = ref<FormInstance>()
const statusForm = reactive<StatusForm>({
  instance_id: '',
  status: '计划',
})

const createRules: FormRules<CreateForm> = {
  flight_no: [{ required: true, message: 'Enter flight number', trigger: 'blur' }],
  flight_date: [{ required: true, message: 'Select date', trigger: 'change' }],
}

const batchRules: FormRules<BatchForm> = {
  flight_no: [{ required: true, message: 'Enter flight number', trigger: 'blur' }],
  start_date: [{ required: true, message: 'Select start date', trigger: 'change' }],
  end_date: [{ required: true, message: 'Select end date', trigger: 'change' }],
}

const updateRules: FormRules<UpdateForm> = {
  scheduled_departure: [{ required: true, message: 'Select departure time', trigger: 'change' }],
  scheduled_arrival: [{ required: true, message: 'Select arrival time', trigger: 'change' }],
  fuel_infra_fee: [{ required: true, message: 'Enter fuel & airport fee', trigger: 'change' }],
}
const statusRules: FormRules<StatusForm> = {
  status: [{ required: true, message: 'Select status', trigger: 'change' }],
}

onMounted(loadInstances)

function normalizeFlightNo(value: string) {
  return value.trim().toUpperCase()
}

async function loadInstances() {
  loading.value = true
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
    if (filters.status) {
      params.status = filters.status
    }
    const page = await flightApi.listInstances(params)
    instances.value = page.items
    total.value = page.total
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  pagination.page = 1
  void loadInstances()
}

function resetFilters() {
  Object.assign(filters, {
    flight_no: '',
    flight_date: '',
    status: '',
  })
  pagination.page = 1
  void loadInstances()
}

function handlePageSizeChange(size: number) {
  pagination.pageSize = size
  pagination.page = 1
  void loadInstances()
}

function openCreate() {
  Object.assign(createForm, {
    flight_no: normalizeFlightNo(filters.flight_no),
    flight_date: filters.flight_date || '',
  })
  createDialogVisible.value = true
  createFormRef.value?.clearValidate()
}

function openBatchGenerate() {
  Object.assign(batchForm, {
    flight_no: normalizeFlightNo(filters.flight_no),
    start_date: '',
    end_date: '',
  })
  batchDialogVisible.value = true
  batchFormRef.value?.clearValidate()
}

function openUpdate(row: FlightInstance) {
  Object.assign(updateForm, {
    instance_id: row.instance_id,
    flight_no: normalizeFlightNo(row.flight_no),
    scheduled_departure: row.scheduled_departure || '',
    scheduled_arrival: row.scheduled_arrival || '',
    fuel_infra_fee: Number(row.fuel_infra_fee ?? 0),
  })
  updateDialogVisible.value = true
  updateFormRef.value?.clearValidate()
}

function validateUpdateTimes() {
  if (updateForm.scheduled_departure && updateForm.scheduled_arrival && updateForm.scheduled_departure > updateForm.scheduled_arrival) {
    ElMessage.error('Departure time cannot be later than arrival time')
    return false
  }
  return true
}
function openStatus(row: FlightInstance) {
  Object.assign(statusForm, {
    instance_id: row.instance_id,
    status: row.status,
  })
  statusDialogVisible.value = true
  statusFormRef.value?.clearValidate()
}

function ensureDateRange(payload: FlightInstanceBatchPayload) {
  if (payload.end_date < payload.start_date) {
    throw new Error('End date cannot be earlier than start date')
  }
}

async function submitCreate() {
  await createFormRef.value?.validate()
  await adminApi.createInstance({
    flight_no: normalizeFlightNo(createForm.flight_no),
    flight_date: createForm.flight_date,
  })
  createDialogVisible.value = false
  ElMessage.success('Flight instance created')
  await loadInstances()
}

async function submitBatch() {
  await batchFormRef.value?.validate()
  const payload: FlightInstanceBatchPayload = {
    flight_no: normalizeFlightNo(batchForm.flight_no),
    start_date: batchForm.start_date,
    end_date: batchForm.end_date,
  }
  try {
    ensureDateRange(payload)
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  const rows = await adminApi.batchGenerateInstances(payload)
  batchDialogVisible.value = false
  ElMessage.success(`Batch generated ${rows.length} instance(s)`)
  await loadInstances()
}

async function submitUpdate() {
  await updateFormRef.value?.validate()
  if (!validateUpdateTimes()) {
    return
  }
  await adminApi.updateInstance(updateForm.instance_id, {
    scheduled_departure: updateForm.scheduled_departure,
    scheduled_arrival: updateForm.scheduled_arrival,
    fuel_infra_fee: updateForm.fuel_infra_fee,
  })
  updateDialogVisible.value = false
  ElMessage.success('Instance updated')
  await loadInstances()
}
async function submitStatus() {
  await statusFormRef.value?.validate()
  await adminApi.updateInstanceStatus(statusForm.instance_id, { status: statusForm.status })
  statusDialogVisible.value = false
  ElMessage.success('Instance status updated')
  await loadInstances()
}

async function deleteInstance(row: FlightInstance) {
  try {
    await ElMessageBox.confirm(`Delete instance ${row.instance_id}?`, 'Delete Flight Instance', { type: 'warning' })
    await adminApi.deleteInstance(row.instance_id)
    ElMessage.success('Instance deleted')
    await loadInstances()
  } catch {
    // 取消删除或后端已提示错误。
  }
}

function openPrices(row: FlightInstance) {
  router.push({ path: '/admin/prices', query: { instance_id: row.instance_id } })
}
</script>

<template>
  <section class="page-section admin-crud-page">
    <div class="toolbar">
      <h1 class="page-title">Flight Instances</h1>
      <div class="toolbar-actions">
        <el-input
          v-model="filters.flight_no"
          clearable
          :prefix-icon="Search"
          maxlength="8"
          placeholder="Flight no."
          class="filter-select"
          @keyup.enter="applyFilters"
        />
        <el-date-picker
          v-model="filters.flight_date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="Operating date"
          class="date-filter"
        />
        <el-select v-model="filters.status" clearable placeholder="Status" class="status-select">
          <el-option v-for="status in instanceStatusOptions" :key="status.value" :label="status.label" :value="status.value" />
        </el-select>
        <el-button :icon="Search" @click="applyFilters">Filter</el-button>
        <el-button @click="resetFilters">Reset</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">Add</el-button>
        <el-button :icon="Plus" @click="openBatchGenerate">Batch Generate</el-button>
        <el-button :icon="Refresh" @click="loadInstances">Refresh</el-button>
      </div>
    </div>

    <el-table v-if="instances.length || loading" v-loading="loading" :data="instances" border row-key="instance_id">
      <el-table-column prop="instance_id" label="Instance ID" min-width="180" />
      <el-table-column prop="flight_no" label="Flight No." width="110" />
      <el-table-column label="Operating Date" width="130">
        <template #default="{ row }">{{ formatDate(row.flight_date) }}</template>
      </el-table-column>
      <el-table-column label="Status" width="120">
        <template #default="{ row }">{{ instanceStatusLabel(row.status) }}</template>
      </el-table-column>
      <el-table-column label="Departure" width="100">
        <template #default="{ row }">{{ formatTime(row.scheduled_departure) }}</template>
      </el-table-column>
      <el-table-column label="Arrival" width="100">
        <template #default="{ row }">{{ formatTime(row.scheduled_arrival) }}</template>
      </el-table-column>
      <el-table-column label="Fuel & Airport" width="120">
        <template #default="{ row }">{{ formatCurrency(row.fuel_infra_fee ?? 0) }}</template>
      </el-table-column>
      <el-table-column prop="economy_left" label="Economy Left" width="120" />
      <el-table-column prop="first_left" label="First Left" width="120" />
      <el-table-column label="Actions" width="300" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :icon="Edit" @click="openUpdate(row)">Edit</el-button>
          <el-button link type="primary" @click="openStatus(row)">Status</el-button>
          <el-button link type="primary" @click="openPrices(row)">Pricing</el-button>
          <el-button link type="danger" :icon="Delete" @click="deleteInstance(row)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>
    <EmptyState v-else title="No Instances" description="No flight instance data." />

    <el-pagination
      v-if="total > 0"
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.pageSize"
      class="pager"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      layout="total, sizes, prev, pager, next"
      @current-change="loadInstances"
      @size-change="handlePageSizeChange"
    />

    <el-dialog v-model="createDialogVisible" title="Add Flight Instance" width="460px" :close-on-click-modal="false">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-position="top">
        <el-form-item label="Flight No." prop="flight_no">
          <el-input v-model="createForm.flight_no" maxlength="8" class="full-width" />
        </el-form-item>
        <el-form-item label="Operating Date" prop="flight_date">
          <el-date-picker
            v-model="createForm.flight_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="Select date"
            class="full-width"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="submitCreate">Save</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchDialogVisible" title="Batch Generate by Flight" width="520px" :close-on-click-modal="false">
      <el-form ref="batchFormRef" :model="batchForm" :rules="batchRules" label-position="top">
        <el-form-item label="Flight No." prop="flight_no">
          <el-input v-model="batchForm.flight_no" maxlength="8" class="full-width" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="Start Date" prop="start_date">
            <el-date-picker
              v-model="batchForm.start_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="Start date"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="End Date" prop="end_date">
            <el-date-picker
              v-model="batchForm.end_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="End date"
              class="full-width"
            />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="batchDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="submitBatch">Generate</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="updateDialogVisible" title="Edit Flight Instance" width="520px" :close-on-click-modal="false">
      <el-form ref="updateFormRef" :model="updateForm" :rules="updateRules" label-position="top">
        <el-form-item label="Instance ID">
          <el-input v-model="updateForm.instance_id" disabled />
        </el-form-item>
        <el-form-item label="Flight No." prop="flight_no">
          <el-input v-model="updateForm.flight_no" maxlength="8" class="full-width" disabled />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="Departure Time" prop="scheduled_departure">
            <el-time-picker v-model="updateForm.scheduled_departure" value-format="HH:mm:ss" format="HH:mm" class="full-width" />
          </el-form-item>
          <el-form-item label="Arrival Time" prop="scheduled_arrival">
            <el-time-picker v-model="updateForm.scheduled_arrival" value-format="HH:mm:ss" format="HH:mm" class="full-width" />
          </el-form-item>
        </div>
        <el-form-item label="Fuel & Airport Fee" prop="fuel_infra_fee">
          <el-input-number v-model="updateForm.fuel_infra_fee" :min="0" :precision="2" :step="10" class="full-width" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="updateDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="submitUpdate">Save</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="statusDialogVisible" title="Update Instance Status" width="420px" :close-on-click-modal="false">
      <el-form ref="statusFormRef" :model="statusForm" :rules="statusRules" label-position="top">
        <el-form-item label="Instance ID">
          <el-input v-model="statusForm.instance_id" disabled />
        </el-form-item>
        <el-form-item label="Status" prop="status">
          <el-select v-model="statusForm.status" class="full-width">
            <el-option v-for="status in instanceStatusOptions" :key="status.value" :label="status.label" :value="status.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statusDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="submitStatus">Save</el-button>
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
  width: 150px;
}

.date-filter {
  width: 150px;
}

.status-select {
  width: 120px;
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
</style>
