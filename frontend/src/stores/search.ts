import { defineStore } from 'pinia'
import type { FlightSearchRequest, FlightSearchResponse } from '@/types/search'

interface SearchState {
  criteria: FlightSearchRequest | null
  result: FlightSearchResponse | null
}

export const useSearchStore = defineStore('search', {
  state: (): SearchState => ({
    criteria: null,
    result: null,
  }),
  actions: {
    setCriteria(criteria: FlightSearchRequest) {
      this.criteria = criteria
    },
    setResult(result: FlightSearchResponse | null) {
      this.result = result
    },
    reset() {
      this.criteria = null
      this.result = null
    },
  },
})
