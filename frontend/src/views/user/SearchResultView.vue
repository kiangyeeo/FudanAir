<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Right } from '@element-plus/icons-vue'
import { flightApi } from '@/api/flight'
import { searchApi } from '@/api/search'
import DirectFlightList from '@/components/flight/DirectFlightList.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import FilterPanel from '@/components/flight/FilterPanel.vue'
import FlightCardSkeleton from '@/components/flight/FlightCardSkeleton.vue'
import NearbyFlightList from '@/components/flight/NearbyFlightList.vue'
import TransitFlightList from '@/components/flight/TransitFlightList.vue'
import { useSearchStore } from '@/stores/search'
import { useAirportStore } from '@/stores/airport'
import { useFlightMetaStore } from '@/stores/flightMeta'
import type { Airline } from '@/types/flight'
import type { CabinClass, SortOrder } from '@/types/common'
import type { DirectFlightCandidate, FlightSearchRequest, NearbyFlightCandidate, TransitCandidate } from '@/types/search'
import { buildAirlineFilter, normalizeAirlineCodes } from '@/utils/searchFilters'

const route = useRoute()
const router = useRouter()
const searchStore = useSearchStore()
const airportStore = useAirportStore()
const flightMetaStore = useFlightMetaStore()
const loading = ref(false)
const searched = ref(false)
const cities = ref<string[]>([])
const airlines = ref<Airline[]>([])
const result = computed(() => searchStore.result)
const totalCount = computed(() => {
  const data = result.value
  if (!data) {
    return 0
  }
  return data.direct.length + data.transit.length + data.nearby.length
})

async function runSearch(payload: FlightSearchRequest) {
  const criteria = normalizeCriteria(payload)
  if (!criteria.dep_city || !criteria.arr_city || !criteria.flight_date) {
    ElMessage.warning('请填写出发城市、到达城市和日期')
    return
  }
  const { price_min: priceMin, price_max: priceMax } = criteria.filters ?? {}
  if (priceMin !== null && priceMin !== undefined && priceMax !== null && priceMax !== undefined && priceMin > priceMax) {
    ElMessage.warning('价格区间上限不能小于下限')
    return
  }

  searched.value = true
  loading.value = true
  searchStore.setCriteria(criteria)
  await router.replace({ name: 'search', query: criteriaToQuery(criteria) })
  try {
    const data = await searchApi.searchFlights(criteria)
    searchStore.setResult(data)
    void flightMetaStore.ensure(collectFlightNos(data))
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  searched.value = false
  searchStore.reset()
  void router.replace({ name: 'search' })
}

function selectFlight(candidate: DirectFlightCandidate | NearbyFlightCandidate) {
  const cabinClass = searchStore.criteria?.filters?.cabin_class ?? '经济舱'
  router.push({
    name: 'booking',
    query: {
      instance_id: candidate.instance_id,
      cabin_class: cabinClass,
      fare_type: '标准',
    },
  })
}

function selectTransit(candidate: TransitCandidate) {
  const cabinClass = searchStore.criteria?.filters?.cabin_class ?? '经济舱'
  router.push({
    name: 'booking',
    query: {
      segments: [candidate.leg1.instance_id, candidate.leg2.instance_id].join(','),
      cabin_class: cabinClass,
      fare_type: '标准',
    },
  })
}

function collectFlightNos(data: import('@/types/search').FlightSearchResponse): string[] {
  const nos: string[] = []
  data.direct.forEach((item) => nos.push(item.flight_no))
  data.nearby.forEach((item) => nos.push(item.flight_no))
  data.transit.forEach((item) => {
    nos.push(item.leg1.flight_no, item.leg2.flight_no)
  })
  return nos
}

async function loadOptions() {
  void airportStore.ensureLoaded()
  const [cityResult, airlineResult] = await Promise.allSettled([
    flightApi.listCities(),
    flightApi.listAirlines(),
  ])
  if (cityResult.status === 'fulfilled') {
    cities.value = cityResult.value
  }
  if (airlineResult.status === 'fulfilled') {
    airlines.value = airlineResult.value
  }
}

function normalizeCriteria(payload: FlightSearchRequest): FlightSearchRequest {
  const airlineFilter = buildAirlineFilter(normalizeAirlineCodes(payload.filters))
  const priceMin = normalizePriceValue(payload.filters?.price_min)
  const priceMax = normalizePriceValue(payload.filters?.price_max)
  return {
    dep_city: payload.dep_city.trim(),
    arr_city: payload.arr_city.trim(),
    flight_date: payload.flight_date,
    filters: {
      ...airlineFilter,
      cabin_class: payload.filters?.cabin_class || null,
      departure_time_range: payload.filters?.departure_time_range ?? null,
      price_min: priceMin,
      price_max: priceMax,
      include_stopover: payload.filters?.include_stopover ?? true,
    },
    sort: {
      field: payload.sort?.field ?? 'price',
      order: payload.sort?.order ?? 'asc',
    },
  }
}

function criteriaToQuery(payload: FlightSearchRequest) {
  const airlineCodes = normalizeAirlineCodes(payload.filters)
  const query: Record<string, string> = {
    dep_city: payload.dep_city,
    arr_city: payload.arr_city,
    flight_date: payload.flight_date,
    sort_field: payload.sort?.field ?? 'price',
    sort_order: payload.sort?.order ?? 'asc',
  }
  if (airlineCodes.length) {
    query.airline_codes = airlineCodes.join(',')
  }
  if (payload.filters?.cabin_class) {
    query.cabin_class = payload.filters.cabin_class
  }
  if (payload.filters?.departure_time_range) {
    query.time_start = payload.filters.departure_time_range[0]
    query.time_end = payload.filters.departure_time_range[1]
  }
  if (payload.filters?.price_min !== null && payload.filters?.price_min !== undefined) {
    query.price_min = String(payload.filters.price_min)
  }
  if (payload.filters?.price_max !== null && payload.filters?.price_max !== undefined) {
    query.price_max = String(payload.filters.price_max)
  }
  if (payload.filters?.include_stopover === false) {
    query.include_stopover = 'false'
  }
  return query
}

function criteriaFromRoute(): FlightSearchRequest | null {
  const depCity = queryText('dep_city')
  const arrCity = queryText('arr_city')
  const flightDate = queryText('flight_date')
  if (!depCity || !arrCity || !flightDate) {
    return null
  }
  const timeStart = queryText('time_start')
  const timeEnd = queryText('time_end')
  const departureTimeRange: [string, string] | null = timeStart && timeEnd ? [timeStart, timeEnd] : null
  return normalizeCriteria({
    dep_city: depCity,
    arr_city: arrCity,
    flight_date: flightDate,
    filters: {
      airline_code: queryText('airline_code'),
      airline_codes: queryTextList('airline_codes'),
      cabin_class: cabinClassQuery(queryText('cabin_class')),
      departure_time_range: departureTimeRange,
      price_min: queryNumber('price_min'),
      price_max: queryNumber('price_max'),
      include_stopover: queryText('include_stopover') !== 'false',
    },
    sort: {
      field: sortFieldQuery(queryText('sort_field')),
      order: sortOrderQuery(queryText('sort_order')),
    },
  })
}

function queryText(key: string): string | null {
  const value = route.query[key]
  if (Array.isArray(value)) {
    return value[0] ?? null
  }
  return value ?? null
}

function queryTextList(key: string): string[] {
  const value = route.query[key]
  const rawValues = Array.isArray(value) ? value : value ? [value] : []
  return rawValues.flatMap((item) => String(item ?? '').split(',')).filter(Boolean)
}

function queryNumber(key: string): number | null {
  const raw = queryText(key)
  if (raw === null || raw === '') {
    return null
  }
  const value = Number(raw)
  return Number.isFinite(value) && value >= 0 ? value : null
}

function normalizePriceValue(value: number | null | undefined): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null
}

function cabinClassQuery(value: string | null): CabinClass | null {
  return value === '经济舱' || value === '头等舱' ? value : null
}

function sortFieldQuery(value: string | null): 'price' | 'duration' | 'departure' {
  return value === 'duration' || value === 'departure' ? value : 'price'
}

function sortOrderQuery(value: string | null): SortOrder {
  return value === 'desc' ? 'desc' : 'asc'
}

onMounted(() => {
  void loadOptions()
  const initial = criteriaFromRoute() ?? searchStore.criteria
  if (initial) {
    void runSearch(initial)
  }
})
</script>

<template>
  <div class="page-shell result-page">
    <aside class="page-section search-sidebar">
      <FilterPanel
        :initial="searchStore.criteria"
        :loading="loading"
        :cities="cities"
        :airlines="airlines"
        @search="runSearch"
        @reset="resetSearch"
      />
    </aside>

    <main class="result-main">
      <div class="page-section summary-bar">
        <div class="route-info">
          <h1 class="page-title">搜索结果</h1>
          <div v-if="searchStore.criteria" class="route">
            <span class="city">{{ searchStore.criteria.dep_city }}</span>
            <el-icon class="arrow"><Right /></el-icon>
            <span class="city">{{ searchStore.criteria.arr_city }}</span>
            <span class="fa-chip date-chip">{{ searchStore.criteria.flight_date }}</span>
          </div>
          <span v-else class="hint">请先输入搜索条件</span>
        </div>
        <div class="count-summary">
          <span class="count-pill direct"><b class="mono-num">{{ result?.direct.length ?? 0 }}</b> 直飞</span>
          <span class="count-pill transit"><b class="mono-num">{{ result?.transit.length ?? 0 }}</b> 中转</span>
          <span class="count-pill nearby"><b class="mono-num">{{ result?.nearby.length ?? 0 }}</b> 临近</span>
        </div>
      </div>

      <div class="result-lists">
        <FlightCardSkeleton v-if="loading" :count="5" />
        <template v-else>
          <EmptyState v-if="!searched && !result" title="等待搜索" description="填写条件后会展示直飞、中转和临近机场方案。" />
          <EmptyState v-else-if="searched && result && totalCount === 0" title="暂无匹配航班" description="可以调整日期、城市或筛选条件后重新搜索。" />
          <template v-else>
            <DirectFlightList :items="result?.direct ?? []" @select="selectFlight" />
            <TransitFlightList :items="result?.transit ?? []" @select="selectTransit" />
            <NearbyFlightList :items="result?.nearby ?? []" @select="selectFlight" />
          </template>
        </template>
      </div>
    </main>
  </div>
</template>

<style scoped lang="scss">
.result-page {
  width: min(1540px, calc(100% - 24px));
  display: grid;
  grid-template-columns: minmax(300px, 320px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
  padding: 20px 0 8px;
}

.search-sidebar,
.result-main {
  min-width: 0;
}

.search-sidebar {
  position: sticky;
  top: calc(var(--fa-header-height) + 16px);
  max-height: calc(100vh - var(--fa-header-height) - 32px);
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.result-main {
  display: grid;
  gap: 16px;
}

.summary-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.route-info .page-title {
  margin-bottom: 14px;
}

.route {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  line-height: 1.4;
}

.route .city {
  font-size: 19px;
  font-weight: 700;
  color: var(--fa-text);
}

.route .arrow {
  color: var(--fa-brand);
  font-size: 17px;
}

.date-chip {
  margin-left: 2px;
  padding: 4px 12px;
  background: var(--fa-brand-soft);
  color: var(--fa-brand);
}

.hint {
  color: var(--fa-text-secondary);
  font-size: 13px;
}

.count-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.count-pill {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 6px 12px;
  border-radius: var(--fa-radius-pill);
  background: var(--fa-surface-2);
  color: var(--fa-text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.count-pill b {
  font-size: 16px;
}

.count-pill.direct b {
  color: var(--fa-brand);
}

.count-pill.transit b {
  color: #722ed1;
}

.count-pill.nearby b {
  color: var(--fa-accent);
}

.result-lists {
  display: grid;
  min-height: 240px;
  gap: 18px;
}

@media (max-width: 900px) {
  .result-page {
    grid-template-columns: 1fr;
  }

  .search-sidebar {
    position: static;
  }

  .summary-bar {
    align-items: flex-start;
    gap: 12px;
    flex-direction: column;
  }
}
</style>
