import { defineStore } from 'pinia'
import { flightApi } from '@/api/flight'

export interface FlightMeta {
  dep_terminal: string | null
  arr_terminal: string | null
  airline_code: string
  airline_name: string | null
}

interface FlightMetaState {
  map: Record<string, FlightMeta>
}

const inflight = new Set<string>()

export const useFlightMetaStore = defineStore('flightMeta', {
  state: (): FlightMetaState => ({
    map: {},
  }),
  getters: {
    depTerminal: (state) => (flightNo?: string | null) =>
      flightNo ? state.map[flightNo]?.dep_terminal ?? '' : '',
    arrTerminal: (state) => (flightNo?: string | null) =>
      flightNo ? state.map[flightNo]?.arr_terminal ?? '' : '',
    airlineName: (state) => (flightNo?: string | null) =>
      (flightNo ? state.map[flightNo]?.airline_name : null) ?? null,
  },
  actions: {
    /** 按需拉取航班的航站楼/航司信息并缓存（已缓存或在途的跳过） */
    async ensure(flightNos: Array<string | null | undefined>) {
      const targets = Array.from(
        new Set(
          flightNos
            .map((no) => (no ?? '').trim())
            .filter((no) => no && !this.map[no] && !inflight.has(no)),
        ),
      )
      if (!targets.length) {
        return
      }
      targets.forEach((no) => inflight.add(no))
      const results = await Promise.allSettled(
        targets.map((no) => flightApi.getFlight(no)),
      )
      const next = { ...this.map }
      results.forEach((result, index) => {
        const no = targets[index]
        inflight.delete(no)
        if (result.status === 'fulfilled') {
          const flight = result.value
          next[no] = {
            dep_terminal: flight.dep_terminal ?? null,
            arr_terminal: flight.arr_terminal ?? null,
            airline_code: flight.airline_code,
            airline_name: flight.airline_name ?? null,
          }
        }
      })
      this.map = next
    },
  },
})
