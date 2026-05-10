<script setup lang="ts">
import { reactive } from 'vue'
import type { FlightSearchRequest } from '@/types/search'

const props = defineProps<{
  loading?: boolean
  initial?: FlightSearchRequest | null
}>()

const emit = defineEmits<{
  search: [payload: FlightSearchRequest]
}>()

const form = reactive<FlightSearchRequest>({
  dep_city: props.initial?.dep_city ?? '上海',
  arr_city: props.initial?.arr_city ?? '北京',
  flight_date: props.initial?.flight_date ?? new Date().toISOString().slice(0, 10),
  filters: props.initial?.filters ?? { include_stopover: true },
  sort: props.initial?.sort ?? { field: 'price', order: 'asc' },
})

function submit() {
  const sort = form.sort ?? { field: 'price', order: 'asc' as const }
  emit('search', {
    ...form,
    filters: { ...form.filters },
    sort: { field: sort.field, order: sort.order },
  })
}
</script>

<template>
  <el-form class="filter-panel" :model="form" label-position="top">
    <el-form-item label="出发城市">
      <el-input v-model="form.dep_city" />
    </el-form-item>
    <el-form-item label="到达城市">
      <el-input v-model="form.arr_city" />
    </el-form-item>
    <el-form-item label="出行日期">
      <el-date-picker v-model="form.flight_date" type="date" value-format="YYYY-MM-DD" />
    </el-form-item>
    <el-form-item label="排序">
      <el-select v-model="form.sort!.field">
        <el-option label="价格" value="price" />
        <el-option label="总时长" value="duration" />
        <el-option label="起飞时间" value="departure" />
      </el-select>
    </el-form-item>
    <el-button type="primary" :loading="loading" @click="submit">搜索</el-button>
  </el-form>
</template>

<style scoped>
.filter-panel {
  display: grid;
  gap: 8px;
}
</style>
