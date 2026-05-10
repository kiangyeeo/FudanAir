<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useSearchStore } from '@/stores/search'
import type { FlightSearchRequest } from '@/types/search'

const router = useRouter()
const searchStore = useSearchStore()

const form = reactive<FlightSearchRequest>({
  dep_city: '上海',
  arr_city: '北京',
  flight_date: new Date().toISOString().slice(0, 10),
  filters: { include_stopover: true },
  sort: { field: 'price', order: 'asc' },
})

function submit() {
  if (!form.dep_city || !form.arr_city || !form.flight_date) {
    ElMessage.warning('请填写出发城市、到达城市和日期')
    return
  }

  const sort = form.sort ?? { field: 'price', order: 'asc' as const }
  searchStore.setCriteria({
    ...form,
    filters: { ...form.filters },
    sort: { field: sort.field, order: sort.order },
  })
  router.push('/search')
}
</script>

<template>
  <div class="page-shell home-view">
    <section class="search-band">
      <h1>FudanAir 航班查询</h1>
      <el-form class="search-form" :model="form" label-position="top">
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

.search-band {
  padding: 20px;
  background: var(--fa-white);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
}

h1 {
  margin: 0 0 16px;
  font-size: 24px;
  letter-spacing: 0;
}

.search-form {
  display: grid;
  grid-template-columns: repeat(4, minmax(150px, 1fr)) 120px;
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
</style>
