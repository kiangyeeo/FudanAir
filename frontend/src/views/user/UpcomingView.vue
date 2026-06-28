<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Calendar, User, Tickets } from '@element-plus/icons-vue'
import AirlineLogo from '@/components/flight/AirlineLogo.vue'
import FlightPath from '@/components/flight/FlightPath.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { orderApi } from '@/api/order'
import { useAirportStore } from '@/stores/airport'
import { useFlightMetaStore } from '@/stores/flightMeta'
import { combineDateTime, formatCountdown, formatTime, minutesBetween, withTerminal } from '@/utils/format'

interface Trip {
  ticket_no: string
  order_no: string
  flight_no: string
  airline_code: string
  passenger: string
  dep_code: string
  arr_code: string
  dep_time: string
  arr_time?: string | null
  flight_date: string
  cabin_class: string
  fare_type: string
  departAt: Date
  has_adjustment: boolean
}

const ISSUED_STATUS = ['已支付', '已完成', '部分退款']

const router = useRouter()
const airportStore = useAirportStore()
const flightMeta = useFlightMetaStore()
const loading = ref(false)
const trips = ref<Trip[]>([])
const now = ref(Date.now())
let timer: number | undefined

const count = computed(() => trips.value.length)

function dateLabel(date: string) {
  const today = new Date().toISOString().slice(0, 10)
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)
  if (date === today) {
    return `今天 ${date}`
  }
  if (date === tomorrow) {
    return `明天 ${date}`
  }
  return date
}

function countdown(trip: Trip) {
  void now.value
  return formatCountdown(trip.departAt)
}

function imminent(trip: Trip) {
  void now.value
  return trip.departAt.getTime() - Date.now() <= 24 * 3600 * 1000
}

async function load() {
  loading.value = true
  try {
    const res = await orderApi.listMine({ page: 1, page_size: 100 })
    const issued = res.items.filter((order) => order.active_count > 0 && ISSUED_STATUS.includes(order.status))
    const details = await Promise.allSettled(issued.map((order) => orderApi.getDetail(order.order_no)))
    const list: Trip[] = []
    for (const result of details) {
      if (result.status !== 'fulfilled') {
        continue
      }
      const order = result.value
      for (const ticket of order.tickets) {
        if (ticket.status !== '有效') {
          continue
        }
        const departAt = combineDateTime(ticket.flight_date, ticket.scheduled_departure)
        if (!departAt || departAt.getTime() <= Date.now()) {
          continue
        }
        list.push({
          ticket_no: ticket.ticket_no,
          order_no: order.order_no,
          flight_no: ticket.flight_no,
          airline_code: ticket.flight_no.slice(0, 2),
          passenger: ticket.passenger.real_name,
          dep_code: ticket.dep_airport_code,
          arr_code: ticket.arr_airport_code,
          dep_time: ticket.scheduled_departure,
          arr_time: ticket.scheduled_arrival,
          flight_date: ticket.flight_date,
          cabin_class: ticket.cabin_class,
          fare_type: ticket.fare_type,
          departAt,
          has_adjustment: Boolean(ticket.has_adjustment),
        })
      }
    }
    list.sort((a, b) => a.departAt.getTime() - b.departAt.getTime())
    trips.value = list
    void flightMeta.ensure(list.map((trip) => trip.flight_no))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
  timer = window.setInterval(() => {
    now.value = Date.now()
  }, 30000)
})

onBeforeUnmount(() => {
  if (timer) {
    window.clearInterval(timer)
  }
})
</script>

<template>
  <div class="page-shell trips-page">
    <section class="page-section trips-head">
      <div>
        <h1 class="page-title">待出行</h1>
        <span class="sub">已购票、尚未出发的行程</span>
      </div>
      <span class="count-pill"><b class="mono-num">{{ count }}</b> 个行程</span>
    </section>

    <div v-if="loading" class="trip-list">
      <div v-for="i in 3" :key="i" class="fa-skeleton skeleton-card" />
    </div>

    <EmptyState
      v-else-if="!trips.length"
      title="暂无待出行行程"
      description="购票成功后，未出发的行程会显示在这里。"
    />

    <div v-else class="trip-list">
      <article
        v-for="(trip, index) in trips"
        :key="trip.ticket_no"
        class="trip-card"
        v-motion
        :initial="{ opacity: 0, y: 16 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 340, delay: index * 60 } }"
      >
        <span class="accent" />
        <div class="trip-body">
          <header class="trip-top">
            <div class="airline">
              <AirlineLogo :code="trip.airline_code" :name="flightMeta.airlineName(trip.flight_no)" :size="34" />
              <div class="airline-meta">
                <strong>{{ flightMeta.airlineName(trip.flight_no) || trip.airline_code }}</strong>
                <span class="mono-num">{{ trip.flight_no }} · {{ trip.cabin_class }}</span>
                <el-tag v-if="trip.has_adjustment" size="small" type="warning" class="adjust-tag">有调整</el-tag>
              </div>
            </div>
            <span class="countdown" :class="{ imminent: imminent(trip) }">距出发 {{ countdown(trip) }}</span>
          </header>

          <div class="trip-route">
            <div class="endpoint">
              <strong class="mono-num">{{ formatTime(trip.dep_time) }}</strong>
              <span>{{ withTerminal(airportStore.display(trip.dep_code), flightMeta.depTerminal(trip.flight_no)) }}</span>
            </div>
            <FlightPath :duration="minutesBetween(trip.dep_time, trip.arr_time)" :stops="0" class="path" />
            <div class="endpoint">
              <strong class="mono-num">{{ formatTime(trip.arr_time) }}</strong>
              <span>{{ withTerminal(airportStore.display(trip.arr_code), flightMeta.arrTerminal(trip.flight_no)) }}</span>
            </div>
          </div>

          <footer class="trip-foot">
            <div class="meta">
              <span class="chip"><el-icon><Calendar /></el-icon>{{ dateLabel(trip.flight_date) }}</span>
              <span class="chip"><el-icon><User /></el-icon>{{ trip.passenger }}</span>
              <span class="chip mono-num"><el-icon><Tickets /></el-icon>{{ trip.ticket_no }}</span>
            </div>
            <el-button text type="primary" @click="router.push(`/orders/${trip.order_no}`)">查看订单</el-button>
          </footer>
        </div>
      </article>
    </div>
  </div>
</template>

<style scoped lang="scss">
.trips-page {
  display: grid;
  gap: 16px;
  padding: 20px 0 8px;
}

.trips-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.trips-head .page-title {
  margin-bottom: 4px;
}

.sub {
  color: var(--fa-text-tertiary);
  font-size: 13px;
}

.count-pill {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 6px 14px;
  border-radius: var(--fa-radius-pill);
  background: var(--fa-brand-soft);
  color: var(--fa-brand);
  font-size: 13px;
  font-weight: 600;
}

.count-pill b {
  font-size: 16px;
}

.trip-list {
  display: grid;
  gap: 14px;
}

.skeleton-card {
  height: 168px;
  border-radius: var(--fa-radius);
}

.trip-card {
  position: relative;
  display: flex;
  background: var(--fa-surface);
  border: 1px solid var(--fa-border);
  border-radius: var(--fa-radius);
  box-shadow: var(--fa-shadow-1);
  overflow: hidden;
  transition: transform var(--fa-dur-base) var(--fa-ease), box-shadow var(--fa-dur-base) var(--fa-ease);
}

.trip-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--fa-shadow-2);
}

.accent {
  flex: 0 0 6px;
  background: var(--fa-grad-brand);
}

.trip-body {
  flex: 1;
  display: grid;
  gap: 14px;
  padding: 18px 22px;
  min-width: 0;
}

.trip-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.airline {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.airline-meta {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.airline-meta strong {
  font-size: 14px;
  font-weight: 600;
}

.adjust-tag {
  justify-self: start;
}
.airline-meta span {
  color: var(--fa-text-tertiary);
  font-size: 12px;
}

.countdown {
  flex: 0 0 auto;
  padding: 4px 12px;
  border-radius: var(--fa-radius-pill);
  background: var(--fa-brand-soft);
  color: var(--fa-brand);
  font-size: 13px;
  font-weight: 700;
}

.countdown.imminent {
  background: var(--fa-accent-soft);
  color: var(--fa-accent);
}

.trip-route {
  display: grid;
  grid-template-columns: minmax(70px, auto) minmax(120px, 1fr) minmax(70px, auto);
  gap: 24px;
  align-items: center;
  max-width: 560px;
}

.endpoint {
  display: grid;
  gap: 3px;
  text-align: center;
}

.endpoint strong {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.endpoint span {
  color: var(--fa-text-secondary);
  font-size: 13px;
  white-space: nowrap;
}

.trip-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--fa-border);
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--fa-text-secondary);
  font-size: 13px;
}

.chip .el-icon {
  color: var(--fa-text-tertiary);
}

@media (max-width: 700px) {
  .trip-route {
    gap: 14px;
  }

  .endpoint strong {
    font-size: 22px;
  }

  .trip-foot {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
