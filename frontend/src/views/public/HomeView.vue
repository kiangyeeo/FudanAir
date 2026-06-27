<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Promotion, Sort, Calendar, Right } from '@element-plus/icons-vue'
import { flightApi } from '@/api/flight'
import CityAutocomplete from '@/components/flight/CityAutocomplete.vue'
import { useSearchStore } from '@/stores/search'
import type { FlightSearchRequest } from '@/types/search'

const router = useRouter()
const searchStore = useSearchStore()
const cities = ref<string[]>([])
const tripType = ref<'oneway' | 'round' | 'multi'>('oneway')

const tripTabs = [
  { value: 'oneway', label: '单程', enabled: true },
  { value: 'round', label: '往返', enabled: false },
  { value: 'multi', label: '多程', enabled: false },
] as const

const hotRoutes = [
  { dep: '上海', arr: '北京' },
  { dep: '上海', arr: '广州' },
  { dep: '北京', arr: '成都' },
  { dep: '深圳', arr: '上海' },
  { dep: '广州', arr: '重庆' },
  { dep: '成都', arr: '西安' },
]

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

function setTripType(value: (typeof tripTabs)[number]['value'], enabled: boolean) {
  if (!enabled) {
    ElMessage.info('往返 / 多程查询敬请期待')
    return
  }
  tripType.value = value
}

function swapCities() {
  const dep = form.dep_city
  form.dep_city = form.arr_city
  form.arr_city = dep
}

function applyHotRoute(route: { dep: string; arr: string }) {
  form.dep_city = route.dep
  form.arr_city = route.arr
  submit()
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
    <div class="hero-decor">
      <span class="cloud cloud-1" />
      <span class="cloud cloud-2" />
      <svg class="hero-plane" viewBox="0 0 24 24" aria-hidden="true">
        <path
          fill="currentColor"
          d="M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2A1.5 1.5 0 0 0 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1l3.5 1v-1.5L13 19v-5.5z"
        />
      </svg>
    </div>

    <div class="page-shell home-view">
      <div class="hero-copy" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 500 } }">
        <img class="hero-emblem" src="/images/brand-emblem.png" alt="FudanAir 航空票务数据库管理系统" />
        <h1>发现更低机票，开启说走就走的旅程</h1>
        <p>直飞 · 中转 · 临近机场，一次搜索三种方案</p>
      </div>

      <section
        class="search-band"
        v-motion
        :initial="{ opacity: 0, y: 28 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 120 } }"
      >
        <div class="trip-tabs">
          <button
            v-for="tab in tripTabs"
            :key="tab.value"
            type="button"
            class="trip-tab"
            :class="{ active: tripType === tab.value, disabled: !tab.enabled }"
            @click="setTripType(tab.value, tab.enabled)"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="search-form">
          <div class="cities">
            <div class="search-field">
              <span class="field-label">出发城市</span>
              <CityAutocomplete v-model="form.dep_city" :cities="cities" placeholder="输入出发城市" />
            </div>
            <button type="button" class="swap-btn" title="交换出发/到达" @click="swapCities">
              <el-icon><Sort /></el-icon>
            </button>
            <div class="search-field">
              <span class="field-label">到达城市</span>
              <CityAutocomplete v-model="form.arr_city" :cities="cities" placeholder="输入到达城市" />
            </div>
          </div>

          <div class="search-field">
            <span class="field-label">出行日期</span>
            <el-date-picker
              v-model="form.flight_date"
              type="date"
              value-format="YYYY-MM-DD"
              :prefix-icon="Calendar"
              class="full-control"
            />
          </div>

          <div class="search-field">
            <span class="field-label">排序</span>
            <el-select v-model="form.sort!.field" class="full-control">
              <el-option label="价格优先" value="price" />
              <el-option label="总时长优先" value="duration" />
              <el-option label="起飞时间优先" value="departure" />
            </el-select>
          </div>

          <el-button type="primary" class="search-button" :icon="Promotion" @click="submit">查询航班</el-button>
        </div>
      </section>

      <section class="hot-routes">
        <div class="hot-head">
          <strong>热门航线</strong>
          <span>点击直达查询</span>
        </div>
        <div class="route-grid">
          <button
            v-for="(route, index) in hotRoutes"
            :key="`${route.dep}-${route.arr}`"
            type="button"
            class="route-card"
            v-motion
            :initial="{ opacity: 0, y: 16 }"
            :enter="{ opacity: 1, y: 0, transition: { duration: 360, delay: 200 + index * 60 } }"
            @click="applyHotRoute(route)"
          >
            <span class="route-cities">
              {{ route.dep }}
              <el-icon class="route-arrow"><Right /></el-icon>
              {{ route.arr }}
            </span>
            <span class="route-tag">查询</span>
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped lang="scss">
.home-hero {
  position: relative;
  min-height: calc(100vh - var(--fa-header-height));
  padding: 96px 0 56px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(5, 24, 56, 0.62) 0%, rgba(8, 30, 66, 0.34) 240px, rgba(242, 245, 250, 0.96) 470px, var(--fa-bg) 600px),
    url('/images/home-hero.jpg') center top / cover no-repeat;
}

.hero-decor {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.cloud {
  position: absolute;
  height: 60px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 100px;
  filter: blur(6px);
}

.cloud-1 {
  top: 70px;
  left: 8%;
  width: 180px;
  animation: fa-float 7s ease-in-out infinite;
}

.cloud-2 {
  top: 130px;
  right: 12%;
  width: 130px;
  animation: fa-float 9s ease-in-out infinite reverse;
}

.hero-plane {
  position: absolute;
  top: 54px;
  right: 18%;
  width: 46px;
  height: 46px;
  color: rgba(255, 255, 255, 0.85);
  transform: rotate(34deg);
  animation: fa-float 6s ease-in-out infinite;
}

.home-view {
  position: relative;
  display: grid;
  gap: 22px;
}

.hero-copy {
  color: #fff;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.35);
}

.hero-emblem {
  display: block;
  width: 78px;
  height: 78px;
  margin-bottom: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 0 0 5px rgba(255, 255, 255, 0.14), 0 12px 30px rgba(0, 0, 0, 0.3);
}

.hero-copy h1 {
  margin: 0 0 8px;
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -0.01em;
}

.hero-copy p {
  margin: 0;
  font-size: 16px;
  opacity: 0.92;
}

.search-band {
  padding: 18px 22px 24px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: var(--fa-radius-lg);
  box-shadow: var(--fa-shadow-3);
  backdrop-filter: blur(8px);
}

.trip-tabs {
  display: inline-flex;
  gap: 4px;
  margin-bottom: 18px;
  padding: 4px;
  background: var(--fa-surface-2);
  border-radius: var(--fa-radius-pill);
}

.trip-tab {
  padding: 6px 20px;
  border: none;
  border-radius: var(--fa-radius-pill);
  background: transparent;
  color: var(--fa-text-secondary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--fa-dur-fast) var(--fa-ease);
}

.trip-tab.active {
  background: var(--fa-surface);
  color: var(--fa-brand);
  box-shadow: var(--fa-shadow-1);
}

.trip-tab.disabled {
  color: var(--fa-text-tertiary);
  cursor: not-allowed;
}

.search-form {
  display: grid;
  grid-template-columns: minmax(0, 2.2fr) minmax(150px, 1fr) minmax(150px, 1fr) auto;
  gap: 14px;
  align-items: end;
}

.cities {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 8px;
  align-items: end;
}

.search-field {
  display: grid;
  gap: 7px;
  min-width: 0;
}

.field-label {
  color: var(--fa-brand-dark);
  font-size: 13px;
  font-weight: 600;
}

.swap-btn {
  display: grid;
  place-items: center;
  width: 40px;
  height: 44px;
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius-sm);
  background: var(--fa-surface);
  color: var(--fa-brand);
  cursor: pointer;
  transition: transform var(--fa-dur-base) var(--fa-ease), border-color var(--fa-dur-fast) var(--fa-ease);
}

.swap-btn:hover {
  border-color: var(--fa-brand);
  transform: rotate(180deg);
}

.full-control {
  width: 100%;
}

.search-field :deep(.el-input__wrapper),
.search-field :deep(.el-select__wrapper) {
  min-height: 44px;
}

.search-button {
  height: 44px;
  padding: 0 30px;
  font-size: 15px;
  font-weight: 600;
  border-radius: var(--fa-radius-sm);
}

.hot-routes {
  padding: 18px 20px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
  box-shadow: var(--fa-shadow-1);
  backdrop-filter: blur(4px);
}

.hot-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 14px;
}

.hot-head strong {
  font-size: 16px;
}

.hot-head span {
  color: var(--fa-text-tertiary);
  font-size: 13px;
}

.route-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.route-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
  background: var(--fa-surface);
  cursor: pointer;
  transition: transform var(--fa-dur-base) var(--fa-ease), box-shadow var(--fa-dur-base) var(--fa-ease),
    border-color var(--fa-dur-fast) var(--fa-ease);
}

.route-card:hover {
  transform: translateY(-3px);
  border-color: var(--fa-brand);
  box-shadow: var(--fa-shadow-2);
}

.route-cities {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--fa-text);
}

.route-arrow {
  color: var(--fa-brand);
}

.route-tag {
  padding: 2px 10px;
  border-radius: var(--fa-radius-pill);
  background: var(--fa-brand-soft);
  color: var(--fa-brand);
  font-size: 12px;
  font-weight: 600;
}

@media (max-width: 900px) {
  .home-hero {
    padding-top: 64px;
  }

  .search-form {
    grid-template-columns: 1fr;
  }

  .cities {
    grid-template-columns: 1fr auto 1fr;
  }

  .search-button {
    width: 100%;
  }
}

@media (max-width: 560px) {
  .hero-copy h1 {
    font-size: 24px;
  }
}
</style>
