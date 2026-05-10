<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { bookingApi } from '@/api/booking'
import PassengerForm from '@/components/order/PassengerForm.vue'
import { useBookingStore } from '@/stores/booking'
import type { BookingRequest } from '@/types/booking'
import type { Passenger } from '@/types/user'

const router = useRouter()
const bookingStore = useBookingStore()
const loading = ref(false)
const passengers = ref<Passenger[]>([{ id_no: '', real_name: '', birth_date: '' }])

const form = reactive<Omit<BookingRequest, 'passengers'>>({
  instance_id: '',
  cabin_class: '经济舱',
  fare_type: '标准',
})

async function submit() {
  const payload: BookingRequest = { ...form, passengers: passengers.value }
  bookingStore.setDraft(payload)
  loading.value = true
  try {
    const order = await bookingApi.createOrder(payload)
    bookingStore.setCurrentOrder(order)
    ElMessage.success('订单已创建')
    router.push(`/payment/${order.order_no}`)
  } finally {
    loading.value = false
  }
}
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
      <h2>乘机人</h2>
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
  margin: 0 0 12px;
  font-size: 16px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
