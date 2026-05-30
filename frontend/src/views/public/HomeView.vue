<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { flightApi } from '@/api/flight'
import CityAutocomplete from '@/components/flight/CityAutocomplete.vue'
import { useAuthStore } from '@/stores/auth'
import { useSearchStore } from '@/stores/search'
import type { FlightSearchRequest } from '@/types/search'
import { Switch as SwitchIcon } from '@element-plus/icons-vue'


const router = useRouter()
const auth = useAuthStore()
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

function swapCities() {
  const oldDepCity = form.dep_city
  form.dep_city = form.arr_city
  form.arr_city = oldDepCity
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
  <div class="page-shell home-view">
    <section class="auth-band">
      <span v-if="auth.currentUser">欢迎 {{ auth.currentUser.name }}</span>
      <el-button v-else type="primary" @click="router.push('/login')">请登录</el-button>
    </section>

    <section class="search-band">
      <h1>FudanAir 航班查询</h1>
      <el-form class="search-form" :model="form" label-position="top">
        <el-form-item label="出发城市">
          <CityAutocomplete v-model="form.dep_city" :cities="cities" placeholder="输入出发城市" />
        </el-form-item>
        <el-form-item label=" " class="swap-form-item">
          <el-button
            class="swap-button"
            circle
            title="交换出发城市和到达城市"
            @click="swapCities"
          >
            <el-icon>
              <SwitchIcon />
            </el-icon>
          </el-button>
        </el-form-item>
        <el-form-item label="到达城市">
          <CityAutocomplete v-model="form.arr_city" :cities="cities" placeholder="输入到达城市" />
        </el-form-item>
        <el-form-item label="出行日期">
          <el-date-picker v-model="form.flight_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="排序">
          <el-select v-model="form.sort!.field">
            <el-option label="价格优先" value="price" />
            <el-option label="总时长优先" value="duration" />
            <el-option label="起飞时间优先" value="departure" />
          </el-select>
        </el-form-item>
        <el-button type="primary" class="search-button" @click="submit">查询航班</el-button>
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
</template>

<style scoped lang="scss">
.home-view {
  display: grid;
  gap: 16px;
}

.auth-band,
.search-band {
  padding: 20px;
  background: var(--fa-white);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
}

.auth-band {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  color: var(--fa-text-secondary);
}

h1 {
  margin: 0 0 16px;
  font-size: 24px;
  letter-spacing: 0;
}

.search-form {
  display: grid;
  grid-template-columns:
    minmax(150px, 1fr)
    44px
    minmax(150px, 1fr)
    minmax(150px, 1fr)
    minmax(150px, 1fr)
    120px;
  gap: 12px;
  align-items: end;
}

.search-button {
  width: 100%;
  margin-bottom: 18px;
}

.city-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

@media (max-width: 900px) {
  .search-form {
    grid-template-columns: 1fr;
  }

  .swap-button {
    margin-bottom: 0;
  }
}
</style>
