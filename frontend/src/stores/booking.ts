import { defineStore } from 'pinia'
import type { BookingFlightSelection, BookingRequest, BookingResponse, BookingStep } from '@/types/booking'
import type { Passenger } from '@/types/user'

interface BookingState {
  step: BookingStep
  draft: BookingRequest | null
  currentOrder: BookingResponse | null
  latestOrderNo: string | null
}

export const useBookingStore = defineStore('booking', {
  state: (): BookingState => ({
    step: 'select-flight',
    draft: null,
    currentOrder: null,
    latestOrderNo: null,
  }),
  actions: {
    setStep(step: BookingStep) {
      this.step = step
    },
    setSelection(selection: BookingFlightSelection) {
      this.draft = {
        ...selection,
        passengers: this.draft?.passengers ?? [],
      }
      this.step = 'passengers'
    },
    setPassengers(passengers: Passenger[]) {
      if (!this.draft) {
        return
      }
      this.draft = { ...this.draft, passengers }
      this.step = passengers.length ? 'confirm' : 'passengers'
    },
    setDraft(draft: BookingRequest | null) {
      this.draft = draft
      this.step = draft ? 'confirm' : 'select-flight'
    },
    setCurrentOrder(order: BookingResponse | null) {
      this.currentOrder = order
      this.latestOrderNo = order?.order_no ?? this.latestOrderNo
      if (order) {
        this.step = 'payment'
      }
    },
    setLatestOrderNo(orderNo: string | null) {
      this.latestOrderNo = orderNo
    },
    finish() {
      this.step = 'completed'
    },
    clearCurrentOrder() {
      this.currentOrder = null
    },
    clear() {
      this.step = 'select-flight'
      this.draft = null
      this.currentOrder = null
      this.latestOrderNo = null
    },
  },
})
