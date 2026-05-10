import { http } from './client'
import type { BookingRequest, BookingResponse, PayResponse } from '@/types/booking'

export const bookingApi = {
  createOrder: (payload: BookingRequest) => http.post<BookingResponse>('/booking', payload),
  pay: (orderNo: string) => http.post<PayResponse>(`/booking/${orderNo}/pay`),
  cancel: (orderNo: string) => http.post<void>(`/booking/${orderNo}/cancel`),
}
