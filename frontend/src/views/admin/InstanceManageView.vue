<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import { adminApi } from '@/api/admin'
import { flightApi } from '@/api/flight'
import { formatCurrency, formatDate, formatTime } from '@/utils/format'
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

const statusOptions: InstanceStatus[] = ['计划', '可订', '已起飞', '已到达', '已取消']
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
  flight_no: [{ required: true, message: '请输入航班号', trigger: 'blur' }],
  flight_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
}

const batchRules: FormRules<BatchForm> = {
  flight_no: [{ required: true, message: '请输入航班号', trigger: 'blur' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
}

const updateRules: FormRules<UpdateForm> = {
  flight_no: [{ required: true, message: '请输入航班号', trigger: 'blur' }],
  scheduled_departure: [{ required: true, message: '请选择起飞时间', trigger: 'change' }],
  scheduled_arrival: [{ required: true, message: '请选择到达时间', trigger: 'change' }],
  fuel_infra_fee: [{ required: true, message: '请输入燃油基建费', trigger: 'change' }],
}
const statusRules: FormRules<StatusForm> = {
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
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
    ElMessage.error('起飞时间不得晚于到达时间')
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
    throw new Error('结束日期不能早于开始日期')
  }
}

async function submitCreate() {
  await createFormRef.value?.validate()
  await adminApi.createInstance({
    flight_no: normalizeFlightNo(createForm.flight_no),
    flight_date: createForm.flight_date,
  })
  createDialogVisible.value = false
  ElMessage.success('航班实例已创建')
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
  ElMessage.success(`批量生成完成，共 ${rows.length} 条`)
  await loadInstances()
}

async function submitUpdate() {
  await updateFormRef.value?.validate()
  if (!validateUpdateTimes()) {
    return
  }
  await adminApi.updateInstance(updateForm.instance_id, {
    flight_no: normalizeFlightNo(updateForm.flight_no),
    scheduled_departure: updateForm.scheduled_departure,
    scheduled_arrival: updateForm.scheduled_arrival,
    fuel_infra_fee: updateForm.fuel_infra_fee,
  })
  updateDialogVisible.value = false
  ElMessage.success('实例信息已更新')
  await loadInstances()
}
async function submitStatus() {
  await statusFormRef.value?.validate()
  await adminApi.updateInstanceStatus(statusForm.instance_id, { status: statusForm.status })
  statusDialogVisible.value = false
  ElMessage.success('实例状态已更新')
  await loadInstances()
}

async function deleteInstance(row: FlightInstance) {
  try {
    await ElMessageBox.confirm(`确认删除实例 ${row.instance_id}？`, '删除航班实例', { type: 'warning' })
    await adminApi.deleteInstance(row.instance_id)
    ElMessage.success('实例已删除')
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
      <h1 class="page-title">实例管理</h1>
      <div class="toolbar-actions">
        <el-input
          v-model="filters.flight_no"
          clearable
          :prefix-icon="Search"
          maxlength="8"
          placeholder="航班号"
          class="filter-select"
          @keyup.enter="applyFilters"
        />
        <el-date-picker
          v-model="filters.flight_date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="执行日期"
          class="date-filter"
        />
        <el-select v-model="filters.status" clearable placeholder="状态" class="status-select">
          <el-option v-for="status in statusOptions" :key="status" :label="status" :value="status" />
        </el-select>
        <el-button :icon="Search" @click="applyFilters">筛选</el-button>
        <el-button @click="resetFilters">重置</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
        <el-button :icon="Plus" @click="openBatchGenerate">批量生成</el-button>
        <el-button :icon="Refresh" @click="loadInstances">刷新</el-button>
      </div>
    </div>

    <el-table v-if="instances.length || loading" v-loading="loading" :data="instances" border row-key="instance_id">
      <el-table-column prop="instance_id" label="实例 ID" min-width="180" />
      <el-table-column prop="flight_no" label="航班号" width="110" />
      <el-table-column label="执行日期" width="130">
        <template #default="{ row }">{{ formatDate(row.flight_date) }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column label="起飞" width="100">
        <template #default="{ row }">{{ formatTime(row.scheduled_departure) }}</template>
      </el-table-column>
      <el-table-column label="到达" width="100">
        <template #default="{ row }">{{ formatTime(row.scheduled_arrival) }}</template>
      </el-table-column>
      <el-table-column label="燃油基建" width="120">
        <template #default="{ row }">{{ formatCurrency(row.fuel_infra_fee ?? 0) }}</template>
      </el-table-column>
      <el-table-column prop="economy_left" label="经济舱余票" width="120" />
      <el-table-column prop="first_left" label="头等舱余票" width="120" />
      <el-table-column label="操作" width="300" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :icon="Edit" @click="openUpdate(row)">编辑</el-button>
          <el-button link type="primary" @click="openStatus(row)">状态</el-button>
          <el-button link type="primary" @click="openPrices(row)">票价</el-button>
          <el-button link type="danger" :icon="Delete" @click="deleteInstance(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <EmptyState v-else title="暂无实例" description="航班实例数据为空。" />

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

    <el-dialog v-model="createDialogVisible" title="新增航班实例" width="460px" :close-on-click-modal="false">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-position="top">
        <el-form-item label="航班号" prop="flight_no">
          <el-input v-model="createForm.flight_no" maxlength="8" class="full-width" />
        </el-form-item>
        <el-form-item label="执行日期" prop="flight_date">
          <el-date-picker
            v-model="createForm.flight_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            class="full-width"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchDialogVisible" title="按航班批量生成" width="520px" :close-on-click-modal="false">
      <el-form ref="batchFormRef" :model="batchForm" :rules="batchRules" label-position="top">
        <el-form-item label="航班号" prop="flight_no">
          <el-input v-model="batchForm.flight_no" maxlength="8" class="full-width" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="开始日期" prop="start_date">
            <el-date-picker
              v-model="batchForm.start_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="开始日期"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="结束日期" prop="end_date">
            <el-date-picker
              v-model="batchForm.end_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="结束日期"
              class="full-width"
            />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitBatch">生成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="updateDialogVisible" title="编辑航班实例" width="520px" :close-on-click-modal="false">
      <el-form ref="updateFormRef" :model="updateForm" :rules="updateRules" label-position="top">
        <el-form-item label="实例 ID">
          <el-input v-model="updateForm.instance_id" disabled />
        </el-form-item>
        <el-form-item label="航班号" prop="flight_no">
          <el-input v-model="updateForm.flight_no" maxlength="8" class="full-width" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="起飞时间" prop="scheduled_departure">
            <el-time-picker v-model="updateForm.scheduled_departure" value-format="HH:mm:ss" format="HH:mm" class="full-width" />
          </el-form-item>
          <el-form-item label="到达时间" prop="scheduled_arrival">
            <el-time-picker v-model="updateForm.scheduled_arrival" value-format="HH:mm:ss" format="HH:mm" class="full-width" />
          </el-form-item>
        </div>
        <el-form-item label="燃油基建费" prop="fuel_infra_fee">
          <el-input-number v-model="updateForm.fuel_infra_fee" :min="0" :precision="2" :step="10" class="full-width" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="updateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitUpdate">保存</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="statusDialogVisible" title="修改实例状态" width="420px" :close-on-click-modal="false">
      <el-form ref="statusFormRef" :model="statusForm" :rules="statusRules" label-position="top">
        <el-form-item label="实例 ID">
          <el-input v-model="statusForm.instance_id" disabled />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="statusForm.status" class="full-width">
            <el-option v-for="status in statusOptions" :key="status" :label="status" :value="status" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statusDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitStatus">保存</el-button>
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
