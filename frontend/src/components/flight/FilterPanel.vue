<script setup lang="ts">
import { reactive, watch } from 'vue'
import CityAutocomplete from '@/components/flight/CityAutocomplete.vue'
import type { Airline } from '@/types/flight'
import type { FlightSearchRequest, SearchFilters, SearchSort } from '@/types/search'
import { buildAirlineFilter, normalizeAirlineCodes } from '@/utils/searchFilters'
import { Switch as SwitchIcon } from '@element-plus/icons-vue'


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
  filters: SearchFormFilters
  sort: SearchSort
}

type SearchFormFilters = {
  airline_codes: string[]
  cabin_class: SearchFilters['cabin_class'] | null
  departure_time_range: NonNullable<SearchFilters['departure_time_range']> | null
  price_min: number | null
  price_max: number | null
  include_stopover: boolean
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
  teleported: true,
}

const pickerPanelProps = {
  teleported: true,
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

function defaultFilters(): SearchFormFilters {
  return {
    airline_codes: [],
    cabin_class: null,
    departure_time_range: null,
    price_min: null,
    price_max: null,
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
  form.filters = {
    airline_codes: normalizeAirlineCodes(criteria.filters),
    cabin_class: criteria.filters?.cabin_class ?? null,
    departure_time_range: criteria.filters?.departure_time_range ?? null,
    price_min: normalizePriceValue(criteria.filters?.price_min),
    price_max: normalizePriceValue(criteria.filters?.price_max),
    include_stopover: criteria.filters?.include_stopover ?? true,
  }
  form.sort = { ...defaultSort(), ...criteria.sort }
}

function buildPayload(): FlightSearchRequest {
  const airlineFilter = buildAirlineFilter(form.filters.airline_codes)
  return {
    dep_city: form.dep_city.trim(),
    arr_city: form.arr_city.trim(),
    flight_date: form.flight_date,
    filters: {
      ...airlineFilter,
      cabin_class: form.filters.cabin_class || null,
      departure_time_range: form.filters.departure_time_range,
      price_min: normalizePriceValue(form.filters.price_min),
      price_max: normalizePriceValue(form.filters.price_max),
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

function normalizePriceValue(value: number | null | undefined): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function swapCities() {
  const dep = form.dep_city
  form.dep_city = form.arr_city
  form.arr_city = dep
}
</script>

<template>
  <el-form class="filter-panel" :model="form" label-position="top">
    <el-form-item label="航线">
      <div class="route-fields">
        <CityAutocomplete v-model="form.dep_city" :cities="cities" :teleported="true" placeholder="出发城市" />
        <button type="button" class="swap-button" title="交换出发/到达" @click="swapCities">
          <el-icon>
            <SwitchIcon />
          </el-icon>
        </button>
        <CityAutocomplete v-model="form.arr_city" :cities="cities" :teleported="true" placeholder="到达城市" />
      </div>
    </el-form-item>
    <el-form-item label="出行日期">
      <el-date-picker v-model="form.flight_date" v-bind="pickerPanelProps" type="date" value-format="YYYY-MM-DD" class="full-width" />
    </el-form-item>
    <el-form-item label="航司">
      <el-select v-model="form.filters.airline_codes" v-bind="selectPanelProps" multiple collapse-tags collapse-tags-tooltip clearable filterable>
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
    <el-form-item label="价格区间">
      <div class="price-range">
        <el-input-number
          v-model="form.filters.price_min"
          :min="0"
          :precision="0"
          :step="100"
          :controls="false"
          placeholder="最低价"
          class="price-input"
        />
        <span class="range-separator">至</span>
        <el-input-number
          v-model="form.filters.price_max"
          :min="0"
          :precision="0"
          :step="100"
          :controls="false"
          placeholder="最高价"
          class="price-input"
        />
      </div>
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

.route-fields {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 6px;
  align-items: center;
  width: 100%;
  min-width: 0;
}

.swap-button {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid var(--fa-border);
  border-radius: 50%;
  background: var(--fa-surface);
  color: var(--fa-brand);
  cursor: pointer;
  transition: transform var(--fa-dur-base) var(--fa-ease), border-color var(--fa-dur-fast) var(--fa-ease);
}

.swap-button:hover {
  border-color: var(--fa-brand);
  transform: rotate(180deg);
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

.filter-panel :deep(.el-input__wrapper),
.filter-panel :deep(.el-select__wrapper),
.filter-panel :deep(.el-date-editor.el-input__wrapper),
.filter-panel :deep(.el-date-editor--timerange.el-input__wrapper),
.filter-panel :deep(.el-segmented) {
  min-height: 40px;
  border: 1px solid #d0d7de;
  border-radius: 3px;
  background: var(--fa-white);
  box-shadow: none !important;
  transition: border-color 0.15s ease;
}

.filter-panel :deep(.el-input__wrapper:hover),
.filter-panel :deep(.el-select__wrapper:hover),
.filter-panel :deep(.el-date-editor.el-input__wrapper:hover),
.filter-panel :deep(.el-date-editor--timerange.el-input__wrapper:hover),
.filter-panel :deep(.el-segmented:hover) {
  border-color: #9aa4b2;
  box-shadow: none !important;
}

.filter-panel :deep(.el-input__wrapper.is-focus),
.filter-panel :deep(.el-select__wrapper.is-focused),
.filter-panel :deep(.el-date-editor.el-input__wrapper.is-focus),
.filter-panel :deep(.el-date-editor--timerange.el-input__wrapper.is-active) {
  border-color: var(--fa-brand);
  box-shadow: none !important;
}

.price-range {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 6px;
  align-items: center;
  width: 100%;
}

.price-input {
  width: 100%;
  min-width: 0;
}

.range-separator {
  color: var(--fa-text-secondary);
  font-size: 13px;
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
