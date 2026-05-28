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
    { required: true, message: '请输入机场三字码', trigger: 'blur' },
    { min: 3, max: 3, message: '机场代码必须为3位', trigger: 'blur' },
  ],
  airport_name: [
    { required: true, message: '请输入机场名称', trigger: 'blur' },
    { max: 128, message: '机场名称不能超过128个字符', trigger: 'blur' },
  ],
  city_name: [{ required: true, message: '请选择所属城市', trigger: 'change' }],
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
    ElMessage.success('机场已新增')
  } else {
    await adminApi.updateAirport(editingIata.value, payload)
    ElMessage.success('机场已更新')
  }
  dialogVisible.value = false
  await loadAirports()
}

async function deleteAirport(row: Airport) {
  try {
    await ElMessageBox.confirm(`确认删除机场 ${row.iata_code}？`, '删除机场', { type: 'warning' })
    await adminApi.deleteAirport(row.iata_code)
    ElMessage.success('机场已删除')
    await loadAirports()
  } catch {
    // 取消删除或后端已提示错误。
  }
}
</script>

<template>
  <section class="page-section admin-crud-page">
    <div class="toolbar">
      <h1 class="page-title">机场管理</h1>
      <div class="toolbar-actions">
        <el-select v-model="cityFilter" clearable filterable placeholder="所属城市" class="filter-select">
          <el-option v-for="city in cities" :key="city" :label="city" :value="city" />
        </el-select>
        <el-button :icon="Search" @click="loadAirports">筛选</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
        <el-button :icon="Refresh" @click="loadAirports">刷新</el-button>
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
      <el-table-column prop="airport_name" label="机场名称" min-width="240" />
      <el-table-column prop="city_name" label="所属城市" width="140" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" :icon="Delete" @click="deleteAirport(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <EmptyState v-else title="暂无机场" description="机场数据为空。" />

    <el-dialog
      v-model="dialogVisible"
      :title="mode === 'create' ? '新增机场' : '编辑机场'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="IATA 三字码" prop="iata_code">
          <el-input v-model="form.iata_code" maxlength="3" />
        </el-form-item>
        <el-form-item label="机场名称" prop="airport_name">
          <el-input v-model="form.airport_name" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="所属城市" prop="city_name">
          <el-select v-model="form.city_name" filterable class="full-width">
            <el-option v-for="city in cities" :key="city" :label="city" :value="city" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
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
