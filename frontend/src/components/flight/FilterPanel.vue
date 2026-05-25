<script setup lang="ts">
import { reactive, watch } from 'vue'
import CityAutocomplete from '@/components/flight/CityAutocomplete.vue'
import type { Airline } from '@/types/flight'
import type { FlightSearchRequest, SearchFilters, SearchSort } from '@/types/search'

const props = withDefaults(defineProps<{
  loading?: boolean
  initial?: FlightSearchRequest | null
  cities?: string[]
  airlines?: Airline[]
}>(), {
  loading: false,
  initial: null,
  cities: () => [],
  airlines: () => [],
})

const emit = defineEmits<{
  search: [payload: FlightSearchRequest]
  reset: []
}>()

type SearchForm = {
  dep_city: string
  arr_city: string
  flight_date: string
  filters: Required<SearchFilters>
  sort: SearchSort
}

const form = reactive<SearchForm>({
  dep_city: '',
  arr_city: '',
  flight_date: '',
  filters: defaultFilters(),
  sort: defaultSort(),
})

const selectPanelProps = {
  fitInputWidth: true,
  teleported: false,
}

const pickerPanelProps = {
  teleported: false,
}

watch(
  () => props.initial,
  (criteria) => {
    applyCriteria(criteria ?? defaultCriteria())
  },
  { immediate: true },
)

function defaultCriteria(): FlightSearchRequest {
  return {
    dep_city: '',
    arr_city: '',
    flight_date: new Date().toISOString().slice(0, 10),
    filters: defaultFilters(),
    sort: defaultSort(),
  }
}

function defaultFilters(): Required<SearchFilters> {
  return {
    airline_code: null,
    cabin_class: null,
    departure_time_range: null,
    include_stopover: true,
  }
}

function defaultSort(): SearchSort {
  return { field: 'price', order: 'asc' }
}

function applyCriteria(criteria: FlightSearchRequest) {
  form.dep_city = criteria.dep_city
  form.arr_city = criteria.arr_city
  form.flight_date = criteria.flight_date
  form.filters = { ...defaultFilters(), ...criteria.filters }
  form.sort = { ...defaultSort(), ...criteria.sort }
}

function buildPayload(): FlightSearchRequest {
  return {
    dep_city: form.dep_city.trim(),
    arr_city: form.arr_city.trim(),
    flight_date: form.flight_date,
    filters: {
      airline_code: form.filters.airline_code || null,
      cabin_class: form.filters.cabin_class || null,
      departure_time_range: form.filters.departure_time_range,
      include_stopover: form.filters.include_stopover,
    },
    sort: { field: form.sort.field, order: form.sort.order },
  }
}

function submit() {
  emit('search', buildPayload())
}

function reset() {
  applyCriteria(defaultCriteria())
  emit('reset')
}
</script>

<template>
  <el-form class="filter-panel" :model="form" label-position="top">
    <el-form-item label="出发城市">
      <CityAutocomplete v-model="form.dep_city" :cities="cities" placeholder="输入出发城市" />
    </el-form-item>
    <el-form-item label="到达城市">
      <CityAutocomplete v-model="form.arr_city" :cities="cities" placeholder="输入到达城市" />
    </el-form-item>
    <el-form-item label="出行日期">
      <el-date-picker v-model="form.flight_date" v-bind="pickerPanelProps" type="date" value-format="YYYY-MM-DD" class="full-width" />
    </el-form-item>
    <el-form-item label="航司">
      <el-select v-model="form.filters.airline_code" v-bind="selectPanelProps" clearable filterable>
        <el-option v-for="airline in airlines" :key="airline.iata_code" :label="`${airline.iata_code} ${airline.airline_name}`" :value="airline.iata_code" />
      </el-select>
    </el-form-item>
    <el-form-item label="舱位">
      <el-select v-model="form.filters.cabin_class" v-bind="selectPanelProps" clearable>
        <el-option label="经济舱" value="经济舱" />
        <el-option label="头等舱" value="头等舱" />
      </el-select>
    </el-form-item>
    <el-form-item label="起飞时间">
      <el-time-picker
        v-model="form.filters.departure_time_range"
        v-bind="pickerPanelProps"
        is-range
        clearable
        value-format="HH:mm:ss"
        start-placeholder="开始"
        end-placeholder="结束"
        class="full-width"
      />
    </el-form-item>
    <el-form-item label="排序">
      <el-select v-model="form.sort.field" v-bind="selectPanelProps">
        <el-option label="价格" value="price" />
        <el-option label="总时长" value="duration" />
        <el-option label="起飞时间" value="departure" />
      </el-select>
    </el-form-item>
    <el-form-item label="顺序">
      <el-segmented v-model="form.sort.order" :options="[{ label: '升序', value: 'asc' }, { label: '降序', value: 'desc' }]" />
    </el-form-item>
    <el-checkbox v-model="form.filters.include_stopover">包含经停航班</el-checkbox>
    <div class="actions">
      <el-button type="primary" :loading="loading" @click="submit">搜索</el-button>
      <el-button @click="reset">重置</el-button>
    </div>
  </el-form>
</template>

<style scoped>
.filter-panel {
  display: grid;
  gap: 8px;
  width: 100%;
  min-width: 0;
}

.filter-panel :deep(.el-form-item),
.filter-panel :deep(.el-form-item__content) {
  min-width: 0;
}

.full-width,
.filter-panel :deep(.el-select),
.filter-panel :deep(.el-date-editor),
.filter-panel :deep(.el-segmented) {
  width: 100%;
  min-width: 0;
  max-width: 100%;
}

.filter-panel :deep(.el-input),
.filter-panel :deep(.el-input__wrapper),
.filter-panel :deep(.el-select__wrapper),
.filter-panel :deep(.el-date-editor.el-input__wrapper),
.filter-panel :deep(.el-date-editor--timerange.el-input__wrapper) {
  width: 100%;
  min-width: 0;
  max-width: 100%;
}

.filter-panel :deep(.el-range-editor.el-input__wrapper) {
  padding-left: 8px;
  padding-right: 8px;
}

.filter-panel :deep(.el-range-input) {
  min-width: 0;
  flex: 1;
}

.filter-panel :deep(.el-range-separator) {
  flex: 0 0 auto;
  padding: 0 4px;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
</style>
