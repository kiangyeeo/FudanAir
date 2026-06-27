import { defineStore } from 'pinia'
import { flightApi } from '@/api/flight'
import { formatAirportName } from '@/utils/format'

interface AirportState {
  /** iata_code -> 原始机场名 */
  names: Record<string, string>
  loaded: boolean
}

let inflight: Promise<void> | null = null

export const useAirportStore = defineStore('airport', {
  state: (): AirportState => ({
    names: {},
    loaded: false,
  }),
  getters: {
    /** 返回去后缀的机场名；未知则回退到三字码，避免空白 */
    display: (state) => (code?: string | null) => {
      if (!code) {
        return '--'
      }
      const raw = state.names[code]
      return raw ? formatAirportName(raw) : code
    },
  },
  actions: {
    /** 仅首次加载机场列表，构建 code -> name 映射，失败时静默回退到三字码 */
    async ensureLoaded() {
      if (this.loaded || inflight) {
        return inflight ?? undefined
      }
      inflight = (async () => {
        try {
          const airports = await flightApi.listAirports()
          const map: Record<string, string> = {}
          for (const airport of airports) {
            map[airport.iata_code] = airport.airport_name
          }
          this.names = map
          this.loaded = true
        } catch {
          // 静默：display() 会回退到三字码
        } finally {
          inflight = null
        }
      })()
      return inflight
    },
  },
})
