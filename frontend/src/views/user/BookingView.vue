<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { bookingApi } from '@/api/booking'
import { passengerApi } from '@/api/passenger'
import PassengerForm from '@/components/order/PassengerForm.vue'
import { useBookingStore } from '@/stores/booking'
import type { BookingRequest } from '@/types/booking'
import type { CabinClass, FareType } from '@/types/common'
import type { Passenger } from '@/types/user'

const router = useRouter()
const route = useRoute()
const bookingStore = useBookingStore()
const loading = ref(false)
const passengerLoading = ref(false)
const savedPassengers = ref<Passenger[]>([])
const selectedSavedIds = ref<string[]>([])
const passengers = ref<Passenger[]>([{ id_no: '', real_name: '', birth_date: '' }])

const form = reactive<Omit<BookingRequest, 'passengers'>>({
  instance_id: '',
  cabin_class: '经济舱',
  fare_type: '标准',
})

const savedPassengerOptions = computed(() =>
  savedPassengers.value.map((item) => ({
    label: `${item.real_name} · ${item.id_no}`,
    value: item.id_no,
  })),
)

async function submit() {
  const payload = normalizePayload()
  if (!payload) {
    return
  }

  bookingStore.setDraft(payload)
  loading.value = true
  try {
    const order = await bookingApi.createOrder(payload)
    bookingStore.setCurrentOrder(order)
    ElMessage.success('订单已创建，请在 15 分钟内支付')
    router.push(`/payment/${order.order_no}`)
  } finally {
    loading.value = false
  }
}

async function loadSavedPassengers() {
  passengerLoading.value = true
  try {
    savedPassengers.value = await passengerApi.list({ silentError: true })
  } catch {
    savedPassengers.value = []
  } finally {
    passengerLoading.value = false
  }
}

function appendSavedPassengers() {
  const selected = savedPassengers.value.filter((item) => selectedSavedIds.value.includes(item.id_no))
  if (!selected.length) {
    ElMessage.warning('请选择常用乘机人')
    return
  }

  const existingIds = new Set(passengers.value.map((item) => item.id_no.trim()).filter(Boolean))
  const additions = selected.filter((item) => !existingIds.has(item.id_no))
  if (!additions.length) {
    ElMessage.warning('所选乘机人已在订单中')
    return
  }

  const current = passengers.value.length === 1 && isBlankPassenger(passengers.value[0]) ? [] : passengers.value
  passengers.value = [...current, ...additions]
  selectedSavedIds.value = []
}

function normalizePayload(): BookingRequest | null {
  const instanceId = form.instance_id.trim()
  if (!instanceId) {
    ElMessage.warning('请填写航班实例 ID')
    return null
  }

  const normalizedPassengers = passengers.value.map((item) => ({
    id_no: item.id_no.trim(),
    real_name: item.real_name.trim(),
    birth_date: item.birth_date,
  }))

  if (!normalizedPassengers.length) {
    ElMessage.warning('请至少填写一位乘机人')
    return null
  }

  const ids = new Set<string>()
  for (const passenger of normalizedPassengers) {
    if (!passenger.id_no || !passenger.real_name || !passenger.birth_date) {
      ElMessage.warning('请完整填写乘机人证件号、姓名和出生日期')
      return null
    }
    if (ids.has(passenger.id_no)) {
      ElMessage.warning(`乘机人证件号重复：${passenger.id_no}`)
      return null
    }
    ids.add(passenger.id_no)
  }

  return {
    instance_id: instanceId,
    cabin_class: form.cabin_class,
    fare_type: form.fare_type,
    passengers: normalizedPassengers,
  }
}

function isBlankPassenger(passenger: Passenger) {
  return !passenger.id_no && !passenger.real_name && !passenger.birth_date
}

function queryText(key: string): string | null {
  const value = route.query[key]
  if (Array.isArray(value)) {
    return value[0] ?? null
  }
  return value ?? null
}

function cabinClass(value: string | null): CabinClass | null {
  return value === '经济舱' || value === '头等舱' ? value : null
}

function fareType(value: string | null): FareType | null {
  return value === '标准' || value === '特价' ? value : null
}

watch(
  () => ({ ...form, passengers: passengers.value }),
  () => {
    bookingStore.setDraft({ ...form, passengers: passengers.value })
  },
  { deep: true },
)

onMounted(() => {
  const instanceId = queryText('instance_id')
  const cabin = cabinClass(queryText('cabin_class'))
  const fare = fareType(queryText('fare_type'))
  const draft = bookingStore.draft

  form.instance_id = instanceId ?? draft?.instance_id ?? ''
  form.cabin_class = cabin ?? draft?.cabin_class ?? '经济舱'
  form.fare_type = fare ?? draft?.fare_type ?? '标准'
  passengers.value = draft?.passengers?.length ? draft.passengers : passengers.value
  bookingStore.setSelection({
    instance_id: form.instance_id,
    cabin_class: form.cabin_class,
    fare_type: form.fare_type,
  })
  void loadSavedPassengers()
})
</script>

<template>
  <div class="page-shell booking-page">
    <section class="page-section">
      <h1 class="page-title">填写订单</h1>
      <el-form :model="form" label-position="top" class="booking-form">
        <el-form-item label="航班实例 ID">
          <el-input v-model="form.instance_id" placeholder="如 CA1234_20260510" />
        </el-form-item>
        <el-form-item label="舱位">
          <el-select v-model="form.cabin_class">
            <el-option label="经济舱" value="经济舱" />
            <el-option label="头等舱" value="头等舱" />
          </el-select>
        </el-form-item>
        <el-form-item label="票价类型">
          <el-select v-model="form.fare_type">
            <el-option label="标准" value="标准" />
            <el-option label="特价" value="特价" />
          </el-select>
        </el-form-item>
      </el-form>
    </section>

    <section class="page-section">
      <div class="section-header">
        <h2>乘机人</h2>
        <div class="passenger-picker">
          <el-select
            v-model="selectedSavedIds"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            :loading="passengerLoading"
            :disabled="!savedPassengerOptions.length"
            placeholder="选择常用乘机人"
          >
            <el-option v-for="item in savedPassengerOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-button :disabled="!savedPassengerOptions.length" @click="appendSavedPassengers">带入</el-button>
        </div>
      </div>
      <PassengerForm v-model="passengers" />
      <div class="actions">
        <el-button type="primary" :loading="loading" @click="submit">提交订单</el-button>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.booking-page {
  display: grid;
  gap: 16px;
}

.booking-form {
  display: grid;
  grid-template-columns: 1fr 160px 160px;
  gap: 12px;
}

h2 {
  margin: 0;
  font-size: 16px;
}

.section-header {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.passenger-picker {
  display: grid;
  grid-template-columns: minmax(220px, 320px) auto;
  gap: 8px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 760px) {
  .booking-form,
  .passenger-picker {
    grid-template-columns: 1fr;
  }
}
</style>
