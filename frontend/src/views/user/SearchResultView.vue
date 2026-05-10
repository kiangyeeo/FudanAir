<script setup lang="ts">
import { computed, ref } from 'vue'
import { searchApi } from '@/api/search'
import DirectFlightList from '@/components/flight/DirectFlightList.vue'
import FilterPanel from '@/components/flight/FilterPanel.vue'
import NearbyFlightList from '@/components/flight/NearbyFlightList.vue'
import TransitFlightList from '@/components/flight/TransitFlightList.vue'
import { useSearchStore } from '@/stores/search'
import type { FlightSearchRequest } from '@/types/search'

const searchStore = useSearchStore()
const loading = ref(false)
const result = computed(() => searchStore.result)

async function runSearch(payload: FlightSearchRequest) {
  loading.value = true
  searchStore.setCriteria(payload)
  try {
    const data = await searchApi.searchFlights(payload)
    searchStore.setResult(data)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-shell result-page">
    <aside class="page-section">
      <FilterPanel :initial="searchStore.criteria" :loading="loading" @search="runSearch" />
    </aside>

    <main class="result-main">
      <div class="page-section summary-bar">
        <h1 class="page-title">搜索结果</h1>
        <span v-if="searchStore.criteria">{{ searchStore.criteria.dep_city }} → {{ searchStore.criteria.arr_city }} · {{ searchStore.criteria.flight_date }}</span>
        <span v-else>请先输入搜索条件</span>
      </div>

      <DirectFlightList :items="result?.direct ?? []" />
      <TransitFlightList :items="result?.transit ?? []" />
      <NearbyFlightList :items="result?.nearby ?? []" />
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
</style>
