<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { flightApi } from '@/api/flight'
import { searchApi } from '@/api/search'
import DirectFlightList from '@/components/flight/DirectFlightList.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import FilterPanel from '@/components/flight/FilterPanel.vue'
import NearbyFlightList from '@/components/flight/NearbyFlightList.vue'
import TransitFlightList from '@/components/flight/TransitFlightList.vue'
import { useSearchStore } from '@/stores/search'
import type { Airline } from '@/types/flight'
import type { CabinClass, SortOrder } from '@/types/common'
import type { DirectFlightCandidate, FlightSearchRequest, NearbyFlightCandidate } from '@/types/search'

const route = useRoute()
const router = useRouter()
const searchStore = useSearchStore()
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

  searched.value = true
  loading.value = true
  searchStore.setCriteria(criteria)
  await router.replace({ name: 'search', query: criteriaToQuery(criteria) })
  try {
    const data = await searchApi.searchFlights(criteria)
    searchStore.setResult(data)
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

async function loadOptions() {
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
  return {
    dep_city: payload.dep_city.trim(),
    arr_city: payload.arr_city.trim(),
    flight_date: payload.flight_date,
    filters: {
      airline_code: payload.filters?.airline_code || null,
      cabin_class: payload.filters?.cabin_class || null,
      departure_time_range: payload.filters?.departure_time_range ?? null,
      include_stopover: payload.filters?.include_stopover ?? true,
    },
    sort: {
      field: payload.sort?.field ?? 'price',
      order: payload.sort?.order ?? 'asc',
    },
  }
}

function criteriaToQuery(payload: FlightSearchRequest) {
  const query: Record<string, string> = {
    dep_city: payload.dep_city,
    arr_city: payload.arr_city,
    flight_date: payload.flight_date,
    sort_field: payload.sort?.field ?? 'price',
    sort_order: payload.sort?.order ?? 'asc',
  }
  if (payload.filters?.airline_code) {
    query.airline_code = payload.filters.airline_code
  }
  if (payload.filters?.cabin_class) {
    query.cabin_class = payload.filters.cabin_class
  }
  if (payload.filters?.departure_time_range) {
    query.time_start = payload.filters.departure_time_range[0]
    query.time_end = payload.filters.departure_time_range[1]
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
      cabin_class: cabinClassQuery(queryText('cabin_class')),
      departure_time_range: departureTimeRange,
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
    <aside class="page-section">
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
        <div>
          <h1 class="page-title">搜索结果</h1>
          <span v-if="searchStore.criteria">{{ searchStore.criteria.dep_city }} → {{ searchStore.criteria.arr_city }} · {{ searchStore.criteria.flight_date }}</span>
          <span v-else>请先输入搜索条件</span>
        </div>
        <div class="count-summary mono-num">
          <span>直飞 {{ result?.direct.length ?? 0 }}</span>
          <span>中转 {{ result?.transit.length ?? 0 }}</span>
          <span>临近 {{ result?.nearby.length ?? 0 }}</span>
        </div>
      </div>

      <div v-loading="loading" class="result-lists">
        <EmptyState v-if="!searched && !result" title="等待搜索" description="填写条件后会展示直飞、中转和临近机场方案。" />
        <EmptyState v-else-if="searched && result && totalCount === 0" title="暂无匹配航班" description="可以调整日期、城市或筛选条件后重新搜索。" />
        <template v-else>
          <DirectFlightList :items="result?.direct ?? []" @select="selectFlight" />
          <TransitFlightList :items="result?.transit ?? []" @select="selectFlight" />
          <NearbyFlightList :items="result?.nearby ?? []" @select="selectFlight" />
        </template>
      </div>
    </main>
  </div>
</template>

<style scoped lang="scss">
.result-page {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
}

.result-main {
  display: grid;
  gap: 14px;
}

.summary-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-bar span {
  color: var(--fa-text-secondary);
  font-size: 13px;
}

.count-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.result-lists {
  display: grid;
  min-height: 240px;
  gap: 14px;
}

@media (max-width: 900px) {
  .result-page {
    grid-template-columns: 1fr;
  }

  .summary-bar {
    align-items: flex-start;
    gap: 10px;
    flex-direction: column;
  }
}
</style>
