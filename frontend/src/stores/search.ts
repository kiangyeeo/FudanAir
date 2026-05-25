import { defineStore } from 'pinia'
import type { FlightSearchRequest, FlightSearchResponse } from '@/types/search'

const SEARCH_CRITERIA_KEY = 'fudan-air:last-search-criteria'

interface SearchState {
  criteria: FlightSearchRequest | null
  result: FlightSearchResponse | null
}

function readStoredCriteria(): FlightSearchRequest | null {
  if (typeof window === 'undefined') {
    return null
  }
  const raw = window.localStorage.getItem(SEARCH_CRITERIA_KEY)
  if (!raw) {
    return null
  }

  try {
    const criteria = JSON.parse(raw) as Partial<FlightSearchRequest>
    if (!criteria.dep_city || !criteria.arr_city || !criteria.flight_date) {
      return null
    }
    return criteria as FlightSearchRequest
  } catch {
    return null
  }
}

function saveCriteria(criteria: FlightSearchRequest | null) {
  if (typeof window === 'undefined') {
    return
  }
  if (!criteria) {
    window.localStorage.removeItem(SEARCH_CRITERIA_KEY)
    return
  }
  window.localStorage.setItem(SEARCH_CRITERIA_KEY, JSON.stringify(criteria))
}

export const useSearchStore = defineStore('search', {
  state: (): SearchState => ({
    criteria: readStoredCriteria(),
    result: null,
  }),
  actions: {
    setCriteria(criteria: FlightSearchRequest) {
      this.criteria = criteria
      saveCriteria(criteria)
    },
    setResult(result: FlightSearchResponse | null) {
      this.result = result
    },
    reset() {
      this.criteria = null
      this.result = null
      saveCriteria(null)
    },
  },
})
