import { defineStore } from 'pinia'
import type { BookingRequest, BookingResponse } from '@/types/booking'

interface BookingState {
  draft: BookingRequest | null
  currentOrder: BookingResponse | null
}

export const useBookingStore = defineStore('booking', {
  state: (): BookingState => ({
    draft: null,
    currentOrder: null,
  }),
  actions: {
    setDraft(draft: BookingRequest | null) {
      this.draft = draft
    },
    setCurrentOrder(order: BookingResponse | null) {
      this.currentOrder = order
    },
    clear() {
      this.draft = null
      this.currentOrder = null
    },
  },
})
