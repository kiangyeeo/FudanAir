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
  { value: 'oneway', label: 'One-way', enabled: true },
  { value: 'round', label: 'Round-trip', enabled: false },
  { value: 'multi', label: 'Multi-city', enabled: false },
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
    ElMessage.info('Round-trip and multi-city search are coming soon')
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
    ElMessage.warning('Enter departure city, arrival city, and date')
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
    <div class="hero-art" aria-hidden="true"></div>

    <div class="home-view">
      <div class="hero-copy" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 500 } }">
        <div class="hero-titles">
          <h1 class="hero-name">FudanAir Airline Ticketing System</h1>
          <p>Nonstop, transfer, and nearby airport options in one search</p>
        </div>
      </div>

      <section
        class="search-band"
        v-motion
        :initial="{ opacity: 0, y: 28 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 120 } }"
      >
        <div class="trip-tabs-wrap">
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
        </div>

        <div class="search-form">
          <div class="cities">
            <div class="search-field">
              <span class="field-label">Departure City</span>
              <CityAutocomplete v-model="form.dep_city" :cities="cities" placeholder="Enter departure city" />
            </div>
            <button type="button" class="swap-btn" title="Swap departure and arrival" @click="swapCities">
              <el-icon><Sort /></el-icon>
            </button>
            <div class="search-field">
              <span class="field-label">Arrival City</span>
              <CityAutocomplete v-model="form.arr_city" :cities="cities" placeholder="Enter arrival city" />
            </div>
          </div>

          <div class="search-field">
            <span class="field-label">Travel Date</span>
            <el-date-picker
              v-model="form.flight_date"
              type="date"
              value-format="YYYY-MM-DD"
              :prefix-icon="Calendar"
              class="full-control"
            />
          </div>

          <div class="search-field">
            <span class="field-label">Sort By</span>
            <el-select v-model="form.sort!.field" class="full-control">
              <el-option label="Price First" value="price" />
              <el-option label="Shortest Duration" value="duration" />
              <el-option label="Earliest Departure" value="departure" />
            </el-select>
          </div>

          <el-button type="primary" class="search-button" :icon="Promotion" @click="submit">Search Flights</el-button>
        </div>
      </section>

      <section class="hot-routes">
        <p class="hot-head">Popular routes · click to search</p>
        <div class="route-pills">
          <button
            v-for="(route, index) in hotRoutes"
            :key="`${route.dep}-${route.arr}`"
            type="button"
            class="route-pill"
            v-motion
            :initial="{ opacity: 0, y: 16 }"
            :enter="{ opacity: 1, y: 0, transition: { duration: 360, delay: 200 + index * 60 } }"
            @click="applyHotRoute(route)"
          >
            {{ route.dep }}
            <el-icon class="route-arrow"><Right /></el-icon>
            {{ route.arr }}
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
  /* 白蓝灰冷色 mesh 渐变：左上青、右上蓝、底部柔灰，整体清透 */
  background:
    radial-gradient(58% 50% at 12% 6%, rgba(54, 198, 255, 0.18) 0%, rgba(54, 198, 255, 0) 60%),
    radial-gradient(52% 46% at 90% -4%, rgba(22, 119, 255, 0.16) 0%, rgba(22, 119, 255, 0) 55%),
    radial-gradient(72% 62% at 72% 104%, rgba(168, 197, 235, 0.22) 0%, rgba(168, 197, 235, 0) 60%),
    linear-gradient(180deg, #eef4fc 0%, #f1f5fb 45%, var(--fa-bg) 100%);
}

/* 品牌水印层：飞机+双子楼线稿，贴底居中，multiply 让白底隐形只留蓝线
   pointer-events:none + 处于内容之下，绝不遮挡操作；顶部 mask 渐隐保护标题/搜索区 */
.hero-art {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: url('/images/home-bg.jpg') no-repeat center center;
  background-size: cover;
  opacity: 0.12;
  mix-blend-mode: multiply;
  /* 仅在标题所在的中上区轻微压一档，保证文字清晰；楼顶/飞机所在的上缘与两侧保留 */
  -webkit-mask-image: radial-gradient(120% 80% at 50% 34%, rgba(0, 0, 0, 0.35) 0%, rgba(0, 0, 0, 0.7) 32%, #000 60%);
  mask-image: radial-gradient(120% 80% at 50% 34%, rgba(0, 0, 0, 0.35) 0%, rgba(0, 0, 0, 0.7) 32%, #000 60%);
}

.home-view {
  position: relative;
  width: min(1040px, calc(100% - 32px));
  margin: 0 auto;
  display: grid;
  gap: 28px;
}

.hero-copy {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
  color: var(--fa-text);
}

.hero-titles {
  display: grid;
  gap: 10px;
  justify-items: center;
}

.hero-name {
  margin: 0;
  font-family: var(--fa-font-serif);
  font-size: 42px;
  font-weight: 900;
  letter-spacing: 0.01em;
  color: var(--fa-brand-dark);
}

.hero-copy p {
  margin: 0;
  font-size: 16px;
  color: var(--fa-text-secondary);
}

.search-band {
  padding: 18px 22px 24px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: var(--fa-radius-lg);
  box-shadow: var(--fa-shadow-3);
  backdrop-filter: blur(8px);
}

.trip-tabs-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 18px;
}

.trip-tabs {
  display: inline-flex;
  gap: 4px;
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

/* el-date-picker 默认 220px 固定宽，需强制撑满栅格列，否则会溢出与下一列重叠 */
.search-field :deep(.el-date-editor),
.search-field :deep(.el-select) {
  width: 100%;
}

.search-field :deep(.el-date-editor) {
  height: 44px;
}

.search-field :deep(.el-input__wrapper),
.search-field :deep(.el-select__wrapper) {
  min-height: 44px;
  height: 44px;
}

.search-button {
  height: 44px;
  padding: 0 30px;
  font-size: 15px;
  font-weight: 600;
  border-radius: var(--fa-radius-sm);
}

.hot-routes {
  display: grid;
  gap: 16px;
  justify-items: center;
  text-align: center;
}

.hot-head {
  margin: 0;
  color: var(--fa-text-tertiary);
  font-size: 14px;
  font-weight: 600;
}

.route-pills {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
}

.route-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 20px;
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius-pill);
  background: var(--fa-surface);
  font-size: 14px;
  font-weight: 600;
  color: var(--fa-text);
  cursor: pointer;
  box-shadow: var(--fa-shadow-1);
  transition: transform var(--fa-dur-base) var(--fa-ease), box-shadow var(--fa-dur-base) var(--fa-ease),
    border-color var(--fa-dur-fast) var(--fa-ease), color var(--fa-dur-fast) var(--fa-ease);
}

.route-pill:hover {
  transform: translateY(-3px);
  border-color: var(--fa-brand);
  color: var(--fa-brand);
  box-shadow: var(--fa-shadow-2);
}

.route-arrow {
  color: var(--fa-brand);
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
  .hero-copy {
    gap: 14px;
  }

  .hero-name {
    font-size: 24px;
  }
}
</style>
