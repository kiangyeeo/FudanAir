<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { flightApi } from '@/api/flight'
import CityAutocomplete from '@/components/flight/CityAutocomplete.vue'
import { useSearchStore } from '@/stores/search'
import type { FlightSearchRequest } from '@/types/search'

const router = useRouter()
const searchStore = useSearchStore()
const cities = ref<string[]>([])

const form = reactive<FlightSearchRequest>({
  dep_city: searchStore.criteria?.dep_city ?? '',
  arr_city: searchStore.criteria?.arr_city ?? '',
  flight_date: searchStore.criteria?.flight_date ?? new Date().toISOString().slice(0, 10),
  filters: { include_stopover: true },
  sort: {
    field: searchStore.criteria?.sort?.field ?? 'price',
    order: searchStore.criteria?.sort?.order ?? 'asc',
  },
})

async function loadCities() {
  try {
    cities.value = await flightApi.listCities()
  } catch {
    cities.value = []
  }
}

function submit() {
  const depCity = form.dep_city.trim()
  const arrCity = form.arr_city.trim()
  if (!depCity || !arrCity || !form.flight_date) {
    ElMessage.warning('请填写出发城市、到达城市和日期')
    return
  }

  const sort = form.sort ?? { field: 'price', order: 'asc' as const }
  const criteria: FlightSearchRequest = {
    dep_city: depCity,
    arr_city: arrCity,
    flight_date: form.flight_date,
    filters: { ...form.filters },
    sort: { field: sort.field, order: sort.order },
  }
  searchStore.setCriteria(criteria)
  router.push({
    name: 'search',
    query: {
      dep_city: criteria.dep_city,
      arr_city: criteria.arr_city,
      flight_date: form.flight_date,
      sort_field: sort.field,
      sort_order: sort.order,
    },
  })
}

onMounted(() => {
  void loadCities()
})
</script>

<template>
  <div class="home-hero">
    <div class="page-shell home-view">
      <section class="search-band">
        <h1>FudanAir 航班查询</h1>
        <el-form class="search-form" :model="form">
          <div class="search-field">
            <span class="field-label">出发城市</span>
            <el-form-item class="field-item">
              <CityAutocomplete v-model="form.dep_city" :cities="cities" placeholder="输入出发城市" />
            </el-form-item>
          </div>

          <div class="search-field">
            <span class="field-label">到达城市</span>
            <el-form-item class="field-item">
              <CityAutocomplete v-model="form.arr_city" :cities="cities" placeholder="输入到达城市" />
            </el-form-item>
          </div>

          <div class="search-field">
            <span class="field-label">出行日期</span>
            <el-form-item class="field-item">
              <el-date-picker v-model="form.flight_date" type="date" value-format="YYYY-MM-DD" class="full-control" />
            </el-form-item>
          </div>

          <div class="search-field">
            <span class="field-label">排序</span>
            <el-form-item class="field-item">
              <el-select v-model="form.sort!.field" class="full-control">
                <el-option label="价格优先" value="price" />
                <el-option label="总时长优先" value="duration" />
                <el-option label="起飞时间优先" value="departure" />
              </el-select>
            </el-form-item>
          </div>

          <div class="search-action">
            <span class="field-label action-label"></span>
            <el-button type="primary" class="search-button" @click="submit">查询航班</el-button>
          </div>
        </el-form>
      </section>

      <section class="page-section city-row">
        <strong>常用城市</strong>
        <el-tag>上海</el-tag>
        <el-tag>北京</el-tag>
        <el-tag>广州</el-tag>
        <el-tag>成都</el-tag>
        <el-tag>深圳</el-tag>
      </section>
    </div>
  </div>
</template>

<style scoped lang="scss">
.home-hero {
  min-height: calc(100vh - var(--fa-header-height));
  padding: 250px 0 44px;
  background:
    linear-gradient(180deg, rgba(12, 35, 68, 0.08) 0%, rgba(12, 35, 68, 0.2) 210px, rgba(245, 247, 250, 0.94) 410px, var(--fa-bg) 560px),
    url('/images/home-hero.jpg') center top / 100% 430px no-repeat;
}

.home-view {
  display: grid;
  gap: 20px;
}

.search-band {
  padding: 40px 38px 42px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 12px;
  box-shadow: 0 18px 45px rgba(20, 45, 85, 0.16);
  backdrop-filter: blur(6px);
}

h1 {
  margin: 0 0 28px;
  color: var(--fa-text);
  font-size: 28px;
  letter-spacing: 0;
}

.search-form {
  display: grid;
  grid-template-columns: repeat(5, minmax(150px, 1fr));
  gap: 18px;
  align-items: start;
}

.search-field,
.search-action {
  display: grid;
  grid-template-rows: 22px 52px;
  gap: 8px;
  min-width: 0;
}

.field-label {
  display: block;
  height: 22px;
  color: var(--fa-brand-dark);
  font-size: 16px;
  font-weight: 600;
  line-height: 22px;
  text-align: left;
}

.action-label {
  visibility: hidden;
}

.field-item {
  width: 100%;
  height: 52px;
  margin: 0;
}

.field-item :deep(.el-form-item__content) {
  width: 100%;
  height: 52px;
  line-height: 1;
}

.field-item :deep(.el-input),
.field-item :deep(.el-select),
.field-item :deep(.el-date-editor) {
  width: 100%;
  height: 52px;
}

.field-item :deep(.el-input__wrapper),
.field-item :deep(.el-select__wrapper) {
  width: 100%;
  min-height: 52px;
  height: 52px;
  background: var(--fa-white);
  border: 1px solid rgba(22, 119, 255, 0.38);
  border-radius: 4px;
  box-shadow: none;
}

.field-item :deep(.el-input__inner),
.field-item :deep(.el-select__placeholder),
.field-item :deep(.el-select__selected-item) {
  font-size: 16px;
}

.full-control {
  width: 100%;
}

.search-button {
  grid-row: 2;
  width: 100%;
  height: 52px;
  margin: 0;
  border-radius: 4px;
  font-size: 16px;
}

.city-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(255, 255, 255, 0.72);
  box-shadow: 0 12px 30px rgba(20, 45, 85, 0.08);
}

@media (max-width: 900px) {
  .home-hero {
    padding-top: 180px;
    background-size: auto 360px;
  }

  .search-form {
    grid-template-columns: 1fr;
  }
}
</style>
